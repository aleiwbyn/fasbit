"""
Servicio de Planificación de Tareas y Optimización de Rutas.
"""

from __future__ import annotations

from typing import Any

from fasbit.domain.exceptions import InvalidRouteQueryError
from fasbit.domain.models import PlannedTask, RouteEvaluation
from fasbit.functional.pipeline import (
    build_dock_schedule_timeline,
    parse_planned_task,
    parse_route_evaluation,
    pipe,
)
from fasbit.infrastructure.prolog_bridge import PrologBridge


class PlannerService:
    """Casos de uso de consulta de rutas, estado de red y planificación de entregas."""

    def __init__(self, bridge: PrologBridge | None = None) -> None:
        self._bridge = bridge or PrologBridge()

    @property
    def bridge(self) -> PrologBridge:
        return self._bridge

    def get_system_snapshot(self) -> dict[str, Any]:
        """Retorna el grafo vial, zonas de recepción, stock actual y órdenes activas."""
        return self._bridge.inspect_knowledge_base()

    def find_optimal_routes(
        self,
        origen: str,
        destino: str = "almacen_central",
        hora_salida_min: float = 440,
        ventana_inicio_min: float = 475,
        plazo_maximo_min: float = 505,
        multa_por_minuto: float = 4.0,
        traffic_overrides: list[dict[str, Any]] | None = None,
    ) -> tuple[RouteEvaluation, ...]:
        """Obtiene todas las rutas factibles ordenadas por puntaje óptimo."""
        if ventana_inicio_min > plazo_maximo_min:
            raise InvalidRouteQueryError(
                "El inicio de ventana horaria no puede ser mayor que el plazo máximo de entrega."
            )

        raw = self._bridge.find_routes(
            origen=origen,
            destino=destino,
            hora_salida_min=hora_salida_min,
            ventana_inicio_min=ventana_inicio_min,
            plazo_maximo_min=plazo_maximo_min,
            multa_por_minuto=multa_por_minuto,
            traffic_overrides=traffic_overrides,
        )
        alternatives = raw.get("alternativas", [])
        return pipe(
            alternatives,
            lambda items: map(parse_route_evaluation, items),
            tuple,
        )

    def generate_schedule(
        self,
        traffic_overrides: list[dict[str, Any]] | None = None,
        stock_overrides: list[dict[str, Any]] | None = None,
        custom_orders: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Genera el plan integral de entregas y el cronograma libre de colapsos."""
        raw = self._bridge.plan_tasks(
            traffic_overrides=traffic_overrides,
            stock_overrides=stock_overrides,
            custom_orders=custom_orders,
        )
        tasks: tuple[PlannedTask, ...] = tuple(
            map(parse_planned_task, raw.get("tareas_planificadas", ()))
        )
        dock_timeline = build_dock_schedule_timeline(tasks)
        return {
            "tareas": tasks,
            "ocupacion_muelles": dock_timeline,
        }

