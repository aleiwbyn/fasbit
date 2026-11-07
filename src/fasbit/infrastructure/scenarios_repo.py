"""
Repositorio declarativo de escenarios simulados.
"""

from __future__ import annotations

import json
from pathlib import Path

from fasbit.config import DEFAULT_SETTINGS
from fasbit.domain.exceptions import ScenarioNotFoundError
from fasbit.domain.models import ScenarioDefinition


class ScenariosRepository:
    """Gestiona la lectura inmutable de escenarios de prueba desde JSON."""

    def __init__(self, scenarios_path: Path | None = None) -> None:
        self._path = scenarios_path or DEFAULT_SETTINGS.scenarios_file

    def list_all(self) -> tuple[ScenarioDefinition, ...]:
        """Carga todos los escenarios configurados."""
        raw_data = json.loads(self._path.read_text(encoding="utf-8"))
        items = raw_data.get("scenarios", [])
        return tuple(
            ScenarioDefinition(
                id=str(item["id"]),
                nombre=str(item["nombre"]),
                descripcion=str(item["descripcion"]),
                traffic_overrides=tuple(item.get("traffic_overrides", ())),
                stock_overrides=tuple(item.get("stock_overrides", ())),
                custom_orders=tuple(item.get("custom_orders", ())),
            )
            for item in items
        )

    def get_by_id(self, scenario_id: str) -> ScenarioDefinition:
        """Obtiene un escenario específico por su identificador único."""
        for scenario in self.list_all():
            if scenario.id == scenario_id:
                return scenario
        raise ScenarioNotFoundError(
            f"No existe el escenario '{scenario_id}'. "
            f"Disponibles: {[s.id for s in self.list_all()]}"
        )

