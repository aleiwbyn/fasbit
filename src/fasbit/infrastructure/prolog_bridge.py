"""
Adaptador de infraestructura para comunicación estructurada Python <-> SWI-Prolog.
Ejecuta consultas en procesos aislados mediante JSON sobre stdin/stdout, garantizando
ausencia de fugas de estado entre simulaciones concurrentes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from fasbit.config import AppSettings, DEFAULT_SETTINGS, discover_swipl_executable
from fasbit.domain.exceptions import PrologEngineError
from fasbit.infrastructure.embedded_prolog import EmbeddedPrologEngine


class PrologBridge:
    """
    Puente desacoplado hacia el motor lógico Prolog.
    Usa `SWI-Prolog` nativo si está instalado en el sistema; de lo contrario,
    ejecuta automáticamente `EmbeddedPrologEngine` leyendo los mismos archivos `.pl`.
    """

    def __init__(
        self,
        settings: AppSettings = DEFAULT_SETTINGS,
        swipl_path: str | None = None,
        force_embedded: bool = False,
    ) -> None:
        self._settings = settings
        self._main_pl: Path = self._settings.prolog_entry
        if not self._main_pl.is_file():
            raise PrologEngineError(f"No se encontró el archivo Prolog principal: {self._main_pl}")

        self._swipl_path: str | None = None if force_embedded else (swipl_path or discover_swipl_executable())
        self._embedded = EmbeddedPrologEngine(self._main_pl.parent)

    @property
    def swipl_executable(self) -> str:
        return self._swipl_path or "embedded-prolog (.pl reader)"

    @property
    def uses_native_swipl(self) -> bool:
        return self._swipl_path is not None

    def query(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Envía una petición JSON al motor Prolog (nativo o embebido) y retorna la respuesta."""
        if not self._swipl_path:
            response = self._embedded.query(payload)
            if response.get("status") != "ok":
                raise PrologEngineError(
                    f"Error lógico reportado por motor Prolog embebido: {response.get('message')}"
                )
            return response

        serialized_input = json.dumps(payload, ensure_ascii=False)
        cmd = [
            self._swipl_path,
            "-q",
            "-f",
            str(self._main_pl),
            "-g",
            "procesar_peticion_stdin, halt.",
        ]

        try:
            proc = subprocess.run(
                cmd,
                input=serialized_input,
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=str(self._main_pl.parent),
                timeout=self._settings.prolog_timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PrologEngineError(
                f"Tiempo de espera agotado ({self._settings.prolog_timeout_sec}s) ejecutando SWI-Prolog."
            ) from exc
        except OSError as exc:
            raise PrologEngineError(f"Fallo al invocar el proceso SWI-Prolog: {exc}") from exc

        stdout_clean = proc.stdout.strip()
        if proc.returncode != 0 or not stdout_clean:
            stderr_msg = proc.stderr.strip() or "Sin salida de error detallada."
            raise PrologEngineError(
                f"SWI-Prolog finalizó con código {proc.returncode}. Detalle: {stderr_msg}"
            )

        try:
            response: dict[str, Any] = json.loads(stdout_clean)
        except json.JSONDecodeError as exc:
            raise PrologEngineError(
                f"Respuesta JSON inválida desde Prolog: {stdout_clean[:250]}"
            ) from exc

        if response.get("status") != "ok":
            raise PrologEngineError(
                f"Error lógico reportado por Prolog: {response.get('message', 'Error desconocido')}"
            )

        return response

    def health_check(self) -> dict[str, Any]:
        """Verifica conectividad y carga correcta de módulos Prolog."""
        return self.query({"action": "health"})

    def inspect_knowledge_base(
        self,
        traffic_overrides: list[dict[str, Any]] | None = None,
        stock_overrides: list[dict[str, Any]] | None = None,
        custom_orders: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Exporta el estado completo de la red, almacén, proveedores y pedidos."""
        return self.query(
            {
                "action": "inspect_state",
                "traffic_overrides": traffic_overrides or [],
                "stock_overrides": stock_overrides or [],
                "custom_orders": custom_orders or [],
            }
        )

    def find_routes(
        self,
        origen: str,
        destino: str = "almacen_central",
        hora_salida_min: float = 440,
        ventana_inicio_min: float = 475,
        plazo_maximo_min: float = 505,
        multa_por_minuto: float = 4.0,
        traffic_overrides: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Calcula todas las rutas factibles ordenadas de la más óptima a la menos eficiente."""
        return self.query(
            {
                "action": "find_routes",
                "origen": origen,
                "destino": destino,
                "hora_salida_min": hora_salida_min,
                "ventana_inicio_min": ventana_inicio_min,
                "plazo_maximo_min": plazo_maximo_min,
                "multa_por_minuto": multa_por_minuto,
                "traffic_overrides": traffic_overrides or [],
            }
        )

    def plan_tasks(
        self,
        traffic_overrides: list[dict[str, Any]] | None = None,
        stock_overrides: list[dict[str, Any]] | None = None,
        custom_orders: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta el planificador integral de entregas y asignación de zonas."""
        return self.query(
            {
                "action": "plan_tasks",
                "traffic_overrides": traffic_overrides or [],
                "stock_overrides": stock_overrides or [],
                "custom_orders": custom_orders or [],
            }
        )

    def compare_simulation(
        self,
        traffic_overrides: list[dict[str, Any]] | None = None,
        stock_overrides: list[dict[str, Any]] | None = None,
        custom_orders: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Compara operación habitual sin planificador frente a planificación FASBIT."""
        return self.query(
            {
                "action": "compare_simulation",
                "traffic_overrides": traffic_overrides or [],
                "stock_overrides": stock_overrides or [],
                "custom_orders": custom_orders or [],
            }
        )

