"""
Servicio de Simulación Comparativa de Escenarios Logísticos.
Evalúa cuantitativamente la mejora en puntualidad, reducción de costos y mitigación de riesgos.
"""

from __future__ import annotations

from fasbit.domain.models import ScenarioDefinition, ScenarioSimulationResult
from fasbit.functional.metrics import (
    compute_baseline_kpis,
    compute_impact_summary,
    compute_optimized_kpis,
)
from fasbit.functional.pipeline import (
    build_dock_schedule_timeline,
    parse_baseline_task,
    parse_planned_task,
)
from fasbit.infrastructure.prolog_bridge import PrologBridge
from fasbit.infrastructure.scenarios_repo import ScenariosRepository


class SimulationService:
    """Ejecuta simulaciones comparativas (Sin Planificador vs Con FASBIT)."""

    def __init__(
        self,
        bridge: PrologBridge | None = None,
        scenarios_repo: ScenariosRepository | None = None,
    ) -> None:
        self._bridge = bridge or PrologBridge()
        self._scenarios_repo = scenarios_repo or ScenariosRepository()

    def list_scenarios(self) -> tuple[ScenarioDefinition, ...]:
        """Retorna los escenarios de simulación disponibles."""
        return self._scenarios_repo.list_all()

    def run_scenario(self, scenario_id: str) -> ScenarioSimulationResult:
        """Ejecuta un escenario predefinido por su ID."""
        scenario = self._scenarios_repo.get_by_id(scenario_id)
        return self.evaluate_definition(scenario)

    def run_all_scenarios(self) -> tuple[ScenarioSimulationResult, ...]:
        """Ejecuta todos los escenarios registrados y retorna sus resultados inmutables."""
        return tuple(map(self.evaluate_definition, self._scenarios_repo.list_all()))

    def evaluate_definition(self, scenario: ScenarioDefinition) -> ScenarioSimulationResult:
        """Evalúa cualquier definición de escenario contra el motor Prolog y métricas funcionales."""
        raw = self._bridge.compare_simulation(
            traffic_overrides=list(scenario.traffic_overrides),
            stock_overrides=list(scenario.stock_overrides),
            custom_orders=list(scenario.custom_orders),
        )

        baseline_tasks = tuple(map(parse_baseline_task, raw.get("escenario_base", ())))
        optimized_tasks = tuple(map(parse_planned_task, raw.get("escenario_optimizado", ())))

        base_kpis = compute_baseline_kpis(baseline_tasks)
        opt_kpis = compute_optimized_kpis(optimized_tasks)
        impact = compute_impact_summary(base_kpis, opt_kpis, optimized_tasks)
        dock_timeline = build_dock_schedule_timeline(optimized_tasks)

        return ScenarioSimulationResult(
            escenario=scenario,
            tareas_base=baseline_tasks,
            tareas_optimizadas=optimized_tasks,
            kpis_base=base_kpis,
            kpis_optimizado=opt_kpis,
            impacto=impact,
            ocupacion_muelles=dock_timeline,
        )

