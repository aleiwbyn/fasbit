"""
Cálculo funcional puro de KPIs logísticos e impacto operativo.
Emplea `map`, `filter` y `functools.reduce` sobre colecciones inmutables.
"""

from __future__ import annotations

from functools import reduce
from typing import Callable, Iterable, TypeVar

from fasbit.domain.models import (
    BaselineTaskEvaluation,
    ImpactSummary,
    PlannedTask,
    StageKPIs,
)

T = TypeVar("T")


def _sum_by(items: tuple[T, ...], selector: Callable[[T], float]) -> float:
    """Suma funcional pura proyectando un atributo numérico."""
    return round(reduce(lambda acc, x: acc + selector(x), items, 0.0), 2)


def _count_where(items: Iterable[T], predicate: Callable[[T], bool]) -> int:
    """Cuenta elementos que satisfacen un predicado puro."""
    return sum(map(lambda _: 1, filter(predicate, items)))


def compute_baseline_kpis(tasks: tuple[BaselineTaskEvaluation, ...]) -> StageKPIs:
    """Calcula KPIs del escenario base (sin planificador) mediante reducción funcional."""
    total = len(tasks)
    if total == 0:
        return StageKPIs(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0)

    on_time = _count_where(tasks, lambda t: t.ruta.estado_puntualidad == "a_tiempo")
    delayed = total - on_time
    punctuality_pct = round((on_time / total) * 100.0, 2)

    total_delay = _sum_by(tasks, lambda t: t.ruta.minutos_retraso)
    avg_transit = round(_sum_by(tasks, lambda t: t.ruta.tiempo_transito_min) / total, 2)
    total_dist = _sum_by(tasks, lambda t: t.ruta.distancia_km)

    transport_cost = _sum_by(tasks, lambda t: t.ruta.costo_transporte_soles)
    fines_cost = _sum_by(tasks, lambda t: t.ruta.costo_multa_soles)
    warehouse_incident_cost = _sum_by(
        tasks,
        lambda t: (
            t.costo_reproceso_zona_soles
            + t.costo_congestion_muelle_soles
            + t.costo_sobrealmacenamiento_soles
        ),
    )
    total_cost = _sum_by(tasks, lambda t: t.costo_operativo_total_soles)

    zone_errors = _count_where(tasks, lambda t: t.error_posicionamiento_zona)
    dock_collapses = _count_where(tasks, lambda t: t.colapso_zona_recepcion)
    overstock_units = int(_sum_by(tasks, lambda t: float(t.unidades_exceso_almacen)))

    return StageKPIs(
        total_pedidos=total,
        entregas_a_tiempo=on_time,
        entregas_retrasadas=delayed,
        tasa_puntualidad_pct=punctuality_pct,
        minutos_retraso_total=total_delay,
        tiempo_transito_promedio_min=avg_transit,
        distancia_total_km=total_dist,
        costo_transporte_soles=transport_cost,
        costo_multas_soles=fines_cost,
        costo_incidencias_almacen_soles=warehouse_incident_cost,
        costo_total_soles=total_cost,
        errores_posicionamiento_zona=zone_errors,
        colapsos_zona_recepcion=dock_collapses,
        unidades_sobrealmacenamiento=overstock_units,
    )


def compute_optimized_kpis(tasks: tuple[PlannedTask, ...]) -> StageKPIs:
    """Calcula KPIs del escenario optimizado por FASBIT mediante reducción funcional."""
    total = len(tasks)
    if total == 0:
        return StageKPIs(0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0)

    on_time = _count_where(tasks, lambda t: t.ruta.estado_puntualidad == "a_tiempo")
    delayed = total - on_time
    punctuality_pct = round((on_time / total) * 100.0, 2)

    total_delay = _sum_by(tasks, lambda t: t.ruta.minutos_retraso)
    avg_transit = round(_sum_by(tasks, lambda t: t.ruta.tiempo_transito_min) / total, 2)
    total_dist = _sum_by(tasks, lambda t: t.ruta.distancia_km)

    transport_cost = _sum_by(tasks, lambda t: t.ruta.costo_transporte_soles)
    fines_cost = _sum_by(tasks, lambda t: t.ruta.costo_multa_soles)
    warehouse_incident_cost = _sum_by(tasks, lambda t: t.costo_sobrealmacenamiento_soles)
    total_cost = _sum_by(tasks, lambda t: t.costo_operativo_total_soles)

    return StageKPIs(
        total_pedidos=total,
        entregas_a_tiempo=on_time,
        entregas_retrasadas=delayed,
        tasa_puntualidad_pct=punctuality_pct,
        minutos_retraso_total=total_delay,
        tiempo_transito_promedio_min=avg_transit,
        distancia_total_km=total_dist,
        costo_transporte_soles=transport_cost,
        costo_multas_soles=fines_cost,
        costo_incidencias_almacen_soles=warehouse_incident_cost,
        costo_total_soles=total_cost,
        errores_posicionamiento_zona=0,
        colapsos_zona_recepcion=0,
        unidades_sobrealmacenamiento=0,
    )


def compute_impact_summary(
    base_kpis: StageKPIs,
    opt_kpis: StageKPIs,
    planned_tasks: tuple[PlannedTask, ...],
) -> ImpactSummary:
    """Evalúa el impacto financiero, social y operativo del planificador FASBIT."""
    punctuality_gain = round(opt_kpis.tasa_puntualidad_pct - base_kpis.tasa_puntualidad_pct, 2)
    delay_reduction = round(base_kpis.minutos_retraso_total - opt_kpis.minutos_retraso_total, 2)
    savings = round(base_kpis.costo_total_soles - opt_kpis.costo_total_soles, 2)
    cost_reduction_pct = (
        round((savings / base_kpis.costo_total_soles) * 100.0, 2)
        if base_kpis.costo_total_soles > 0
        else 0.0
    )

    excess_blocked = int(_sum_by(planned_tasks, lambda t: float(t.unidades_exceso_evitadas)))
    stockout_alerts_handled = _count_where(
        planned_tasks, lambda t: t.estado_stock_previo == "critico_riesgo_quiebre"
    )

    return ImpactSummary(
        mejora_puntualidad_pp=punctuality_gain,
        reduccion_retrasos_min=delay_reduction,
        ahorro_total_soles=savings,
        reduccion_costo_pct=cost_reduction_pct,
        errores_zona_mitigados=base_kpis.errores_posicionamiento_zona,
        colapsos_muelle_evitados=base_kpis.colapsos_zona_recepcion,
        unidades_exceso_bloqueadas=excess_blocked,
        alertas_quiebre_priorizadas=stockout_alerts_handled,
    )

