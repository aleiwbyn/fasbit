"""
Pruebas de integración del motor de inferencia lógica SWI-Prolog.
Verifica rutas óptimas, restricciones de tráfico, zonas de recepción y stock.
"""

from __future__ import annotations

from fasbit.infrastructure.prolog_bridge import PrologBridge
from fasbit.services.planner_service import PlannerService


def test_prolog_health_and_snapshot() -> None:
    bridge = PrologBridge()
    health = bridge.health_check()
    assert health["status"] == "ok"
    assert health["modules_loaded"] is True

    snap = bridge.inspect_knowledge_base()
    assert len(snap["ubicaciones"]) >= 10
    assert len(snap["tramos"]) >= 15
    assert len(snap["zonas_recepcion"]) == 4
    assert len(snap["pedidos"]) == 5


def test_route_optimization_avoids_congested_javier_prado() -> None:
    planner = PlannerService()
    routes = planner.find_optimal_routes(
        origen="puerto_callao",
        destino="almacen_central",
        hora_salida_min=430,
        ventana_inicio_min=475,
        plazo_maximo_min=500,
        multa_por_minuto=4.5,
    )
    assert len(routes) >= 3
    best = routes[0]
    assert best.estado_puntualidad == "a_tiempo"
    assert best.minutos_retraso == 0.0
    assert "nodo_javier_prado" not in best.nodos


def test_dynamic_traffic_override_reroutes_via_ramiro_priale() -> None:
    planner = PlannerService()
    routes = planner.find_optimal_routes(
        origen="polo_norte_indep",
        destino="almacen_central",
        hora_salida_min=440,
        ventana_inicio_min=485,
        plazo_maximo_min=506,
        multa_por_minuto=4.0,
        traffic_overrides=[
            {"origen": "nodo_evitamiento", "destino": "almacen_central", "nivel": "critico"}
        ],
    )
    best = routes[0]
    assert "nodo_ramiro_priale" in best.nodos


def test_planner_enforces_zone_compatibility_and_stock_caps() -> None:
    planner = PlannerService()
    schedule = planner.generate_schedule()
    tasks = {t.id_pedido: t for t in schedule["tareas"]}

    # ped_001 es refrigerado: debe corregirse de zona_b_seco a zona_a_frio
    ped1 = tasks["ped_001"]
    assert ped1.zona_habitual_proveedor == "zona_b_seco"
    assert ped1.zona_asignada == "zona_a_frio"
    assert ped1.accion_zona == "corregida_zona_incompatible"
    assert ped1.prioridad_stock == 1

    # ped_005 solicita 90 empaques cuando solo caben 50 (470/520) y pide zona_a_frio (incompatible)
    ped5 = tasks["ped_005"]
    assert ped5.cantidad_solicitada == 90
    assert ped5.cantidad_aceptada == 50
    assert ped5.unidades_exceso_evitadas == 40
    assert ped5.decision_almacen == "recepcion_parcial_tope_almacen"
    assert ped5.zona_asignada == "zona_d_multiuso"


def test_embedded_prolog_fallback_matches_native_swipl_across_all_scenarios() -> None:
    """
    Garantiza que cualquier usuario en VS Code sin `swipl` instalado obtenga
    exactamente los mismos resultados leyendo los archivos `.pl` del proyecto.
    """
    from fasbit.services.simulation_service import SimulationService

    native_bridge = PrologBridge(force_embedded=False)
    embedded_bridge = PrologBridge(force_embedded=True)

    assert not embedded_bridge.uses_native_swipl
    assert embedded_bridge.health_check()["engine"] == "prolog_embedded_kb"

    if native_bridge.uses_native_swipl:
        sim_native = SimulationService(bridge=native_bridge).run_all_scenarios()
        sim_embedded = SimulationService(bridge=embedded_bridge).run_all_scenarios()

        for r_nat, r_emb in zip(sim_native, sim_embedded):
            assert r_nat.kpis_base == r_emb.kpis_base
            assert r_nat.kpis_optimizado == r_emb.kpis_optimizado
            assert r_nat.impacto == r_emb.impacto
            assert r_nat.tareas_optimizadas == r_emb.tareas_optimizadas

