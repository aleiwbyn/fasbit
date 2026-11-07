"""
Pruebas de simulación de escenarios e impacto operativo, social y financiero.
"""

from __future__ import annotations

from fasbit.services.simulation_service import SimulationService


def test_all_predefined_scenarios_improve_kpis_and_prevent_collapses() -> None:
    sim_service = SimulationService()
    results = sim_service.run_all_scenarios()
    assert len(results) == 4

    for res in results:
        # El planificador FASBIT elimina al 100% errores de zona y colapsos de recepción
        assert res.kpis_optimizado.errores_posicionamiento_zona == 0
        assert res.kpis_optimizado.colapsos_zona_recepcion == 0
        assert res.kpis_optimizado.unidades_sobrealmacenamiento == 0

        # Reduce costos totales, disminuye retrasos y mejora puntualidad frente al escenario habitual
        assert res.impacto.ahorro_total_soles > 0
        assert res.impacto.reduccion_retrasos_min > 0
        assert res.impacto.mejora_puntualidad_pp > 0

    estandar = next(r for r in results if r.escenario.id == "hora_punta_estandar")
    assert estandar.kpis_optimizado.tasa_puntualidad_pct == 100.0
    assert estandar.impacto.mejora_puntualidad_pp >= 80.0


def test_dock_pressure_scenario_prevents_simultaneous_collapse() -> None:
    sim_service = SimulationService()
    res = sim_service.run_scenario("presion_muelles_simultanea")
    assert res.kpis_base.colapsos_zona_recepcion >= 1
    assert res.kpis_optimizado.colapsos_zona_recepcion == 0
    assert res.impacto.colapsos_muelle_evitados >= 1
