"""
Entidades inmutables de dominio (paradigma funcional).
Todas las estructuras emplean `dataclass(frozen=True)` y tuplas inmutables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def minutes_to_hhmm(minutes: float) -> str:
    """Convierte minutos desde medianoche (ej. 452.5) a formato 'HH:MM'."""
    rounded = int(round(minutes))
    hours = (rounded // 60) % 24
    mins = rounded % 60
    return f"{hours:02d}:{mins:02d}"


def hhmm_to_minutes(hhmm: str) -> int:
    """Convierte cadena 'HH:MM' a minutos enteros desde las 00:00."""
    parts = hhmm.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Formato de hora inválido '{hhmm}', se esperaba HH:MM.")
    hours, mins = int(parts[0]), int(parts[1])
    if not (0 <= hours < 24 and 0 <= mins < 60):
        raise ValueError(f"Hora fuera de rango '{hhmm}'.")
    return hours * 60 + mins


@dataclass(frozen=True)
class RoadSegmentStep:
    """Tramo vial recorrido dentro de una ruta."""

    origen: str
    destino: str
    distancia_km: float
    tiempo_base_min: float
    tiempo_real_min: float
    costo_soles: float
    trafico: str


@dataclass(frozen=True)
class RouteEvaluation:
    """Resultado evaluado de una ruta entre proveedor y almacén."""

    nodos: tuple[str, ...]
    tramos: tuple[RoadSegmentStep, ...]
    distancia_km: float
    tiempo_transito_min: float
    hora_salida_min: float
    hora_llegada_min: float
    estado_puntualidad: str
    minutos_retraso: float
    minutos_espera_ventana: float
    costo_transporte_soles: float
    costo_multa_soles: float
    costo_total_ruta_soles: float
    puntaje_optimizacion: float = 0.0

    @property
    def hora_salida_hhmm(self) -> str:
        return minutes_to_hhmm(self.hora_salida_min)

    @property
    def hora_llegada_hhmm(self) -> str:
        return minutes_to_hhmm(self.hora_llegada_min)


@dataclass(frozen=True)
class PlannedTask:
    """Tarea de abastecimiento planificada óptimamente por FASBIT."""

    id_pedido: str
    id_proveedor: str
    nombre_proveedor: str
    origen: str
    categoria: str
    prioridad_stock: int
    estado_stock_previo: str
    stock_antes: int
    stock_despues: int
    cantidad_solicitada: int
    cantidad_aceptada: int
    unidades_exceso_evitadas: int
    decision_almacen: str
    volumen_efectivo_m3: float
    ventana_inicio_min: float
    plazo_maximo_min: float
    zona_habitual_proveedor: str
    zona_asignada: str
    nombre_zona_asignada: str
    accion_zona: str
    inicio_descarga_min: float
    fin_descarga_min: float
    espera_muelle_min: float
    rutas_evaluadas: int
    ruta: RouteEvaluation
    costo_sobrealmacenamiento_soles: float
    costo_operativo_total_soles: float


@dataclass(frozen=True)
class BaselineTaskEvaluation:
    """Resultado de entrega sin planificador (ruta y muelle habitual del proveedor)."""

    id_pedido: str
    id_proveedor: str
    nombre_proveedor: str
    origen: str
    categoria: str
    cantidad_solicitada: int
    unidades_exceso_almacen: int
    ventana_inicio_min: float
    plazo_maximo_min: float
    zona_intentada: str
    nombre_zona_intentada: str
    error_posicionamiento_zona: bool
    colapso_zona_recepcion: bool
    inicio_recepcion_min: float
    fin_recepcion_min: float
    ruta: RouteEvaluation
    costo_reproceso_zona_soles: float
    costo_congestion_muelle_soles: float
    costo_sobrealmacenamiento_soles: float
    costo_operativo_total_soles: float


@dataclass(frozen=True)
class StageKPIs:
    """Indicadores agregados para un conjunto de entregas (base u optimizado)."""

    total_pedidos: int
    entregas_a_tiempo: int
    entregas_retrasadas: int
    tasa_puntualidad_pct: float
    minutos_retraso_total: float
    tiempo_transito_promedio_min: float
    distancia_total_km: float
    costo_transporte_soles: float
    costo_multas_soles: float
    costo_incidencias_almacen_soles: float
    costo_total_soles: float
    errores_posicionamiento_zona: int
    colapsos_zona_recepcion: int
    unidades_sobrealmacenamiento: int


@dataclass(frozen=True)
class ImpactSummary:
    """Impacto cuantitativo obtenido al aplicar el planificador FASBIT."""

    mejora_puntualidad_pp: float
    reduccion_retrasos_min: float
    ahorro_total_soles: float
    reduccion_costo_pct: float
    errores_zona_mitigados: int
    colapsos_muelle_evitados: int
    unidades_exceso_bloqueadas: int
    alertas_quiebre_priorizadas: int


@dataclass(frozen=True)
class ScenarioDefinition:
    """Definición declarativa de un escenario de simulación."""

    id: str
    nombre: str
    descripcion: str
    traffic_overrides: tuple[dict[str, Any], ...] = ()
    stock_overrides: tuple[dict[str, Any], ...] = ()
    custom_orders: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ScenarioSimulationResult:
    """Resultado comparativo integral de un escenario simulado."""

    escenario: ScenarioDefinition
    tareas_base: tuple[BaselineTaskEvaluation, ...]
    tareas_optimizadas: tuple[PlannedTask, ...]
    kpis_base: StageKPIs
    kpis_optimizado: StageKPIs
    impacto: ImpactSummary
    ocupacion_muelles: tuple[dict[str, Any], ...]

