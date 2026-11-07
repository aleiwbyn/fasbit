"""
Interfaz de Línea de Comandos (CLI) de FASBIT.
Permite ejecutar diagnósticos, planificación, cálculo de rutas, simulaciones y servidor Web.
"""

from __future__ import annotations

import argparse
import sys

import uvicorn

from fasbit.domain.models import ScenarioSimulationResult, hhmm_to_minutes, minutes_to_hhmm
from fasbit.services.planner_service import PlannerService
from fasbit.services.simulation_service import SimulationService


def _print_header(title: str) -> None:
    line = "=" * 88
    print(f"\n{line}\n  {title}\n{line}")


def _cmd_status() -> int:
    planner = PlannerService()
    health = planner.bridge.health_check()
    snapshot = planner.get_system_snapshot()

    _print_header("FASBIT - Estado del Motor Lógico y Base de Conocimientos")
    print(f"  Motor Prolog     : {health.get('engine')} ({planner.bridge.swipl_executable})")
    print(f"  Estado           : {health.get('status').upper()}")
    print(f"  Ubicaciones red  : {len(snapshot['ubicaciones'])} nodos")
    print(f"  Tramos viales    : {len(snapshot['tramos'])} aristas dirigidas")
    print(f"  Zonas recepción  : {len(snapshot['zonas_recepcion'])} muelles configurados")
    print(f"  Categorías stock : {len(snapshot['inventario'])} líneas de inventario")
    print(f"  Proveedores      : {len(snapshot['proveedores'])} empresas registradas")
    print(f"  Pedidos activos  : {len(snapshot['pedidos'])} órdenes de entrega\n")

    print("  Alertas actuales de inventario:")
    for item in snapshot["inventario"]:
        marker = "[CRITICO]" if item["estado_criticidad"] == "critico_riesgo_quiebre" else "[OK]     "
        print(
            f"    {marker} {item['categoria']:<22} "
            f"Stock: {item['stock_actual']:>3}/{item['capacidad_maxima']:<3} "
            f"(Mínimo seguridad: {item['stock_minimo']})"
        )
    return 0


def _cmd_plan() -> int:
    planner = PlannerService()
    schedule = planner.generate_schedule()
    tasks = schedule["tareas"]

    _print_header("FASBIT - Planificación Óptima de Entregas y Muelles de Recepción")
    for t in tasks:
        llegada = minutes_to_hhmm(t.ruta.hora_llegada_min)
        plazo = minutes_to_hhmm(t.plazo_maximo_min)
        desc_ini = minutes_to_hhmm(t.inicio_descarga_min)
        desc_fin = minutes_to_hhmm(t.fin_descarga_min)
        ruta_str = " -> ".join(t.ruta.nodos)
        print(
            f"  [{t.id_pedido}] {t.nombre_proveedor} ({t.categoria}) | Prioridad Stock: P{t.prioridad_stock}"
        )
        print(f"    Ruta óptima ({t.rutas_evaluadas} eval.): {ruta_str}")
        print(
            f"    Llegada: {llegada} (Plazo máx: {plazo}) -> {t.ruta.estado_puntualidad.upper()} | "
            f"Costo Ruta: S/ {t.costo_operativo_total_soles:.2f}"
        )
        print(
            f"    Recepción: {t.nombre_zona_asignada} [{desc_ini} - {desc_fin}] "
            f"({t.accion_zona}) | Unidades aceptadas: {t.cantidad_aceptada}/{t.cantidad_solicitada}\n"
        )
    return 0


def _cmd_routes(origen: str, salida_hhmm: str, plazo_hhmm: str) -> int:
    planner = PlannerService()
    salida_min = hhmm_to_minutes(salida_hhmm)
    plazo_min = hhmm_to_minutes(plazo_hhmm)
    ventana_ini = max(salida_min, plazo_min - 30)

    routes = planner.find_optimal_routes(
        origen=origen,
        hora_salida_min=salida_min,
        ventana_inicio_min=ventana_ini,
        plazo_maximo_min=plazo_min,
    )
    _print_header(f"FASBIT - Rutas Evaluadas desde '{origen}' (Salida {salida_hhmm}, Plazo {plazo_hhmm})")
    if not routes:
        print("  No se encontraron rutas factibles para el origen indicado.")
        return 1

    for idx, r in enumerate(routes, start=1):
        tag = "OPTIMA" if idx == 1 else f"ALT #{idx}"
        print(
            f"  [{tag}] {' -> '.join(r.nodos)}\n"
            f"          Distancia: {r.distancia_km:.1f} km | Tránsito: {r.tiempo_transito_min:.1f} min | "
            f"Llegada: {r.hora_llegada_hhmm} ({r.estado_puntualidad}) | "
            f"Costo Total: S/ {r.costo_total_ruta_soles:.2f} (Multa: S/ {r.costo_multa_soles:.2f})"
        )
    return 0


def _render_simulation_result(res: ScenarioSimulationResult) -> None:
    _print_header(res.escenario.nombre)
    print(f"  {res.escenario.descripcion}\n")
    b = res.kpis_base
    o = res.kpis_optimizado
    imp = res.impacto

    print(f"  {'Indicador':<38} | {'Sin Planificador':>18} | {'Con FASBIT':>18}")
    print("  " + "-" * 80)
    print(f"  {'Tasa de Puntualidad (%)':<38} | {b.tasa_puntualidad_pct:>17.1f}% | {o.tasa_puntualidad_pct:>17.1f}%")
    print(f"  {'Entregas a Tiempo / Total':<38} | {f'{b.entregas_a_tiempo}/{b.total_pedidos}':>18} | {f'{o.entregas_a_tiempo}/{o.total_pedidos}':>18}")
    print(f"  {'Minutos Totales de Retraso':<38} | {b.minutos_retraso_total:>14.1f} min | {o.minutos_retraso_total:>14.1f} min")
    print(f"  {'Costo de Transporte (S/)':<38} | {b.costo_transporte_soles:>18.2f} | {o.costo_transporte_soles:>18.2f}")
    print(f"  {'Multas por Retraso (S/)':<38} | {b.costo_multas_soles:>18.2f} | {o.costo_multas_soles:>18.2f}")
    print(f"  {'Sobrecostos Recepción / Almacén (S/)':<38} | {b.costo_incidencias_almacen_soles:>18.2f} | {o.costo_incidencias_almacen_soles:>18.2f}")
    print(f"  {'COSTO OPERATIVO TOTAL (S/)':<38} | {b.costo_total_soles:>18.2f} | {o.costo_total_soles:>18.2f}")
    print(f"  {'Errores de Posicionamiento en Zona':<38} | {b.errores_posicionamiento_zona:>18} | {o.errores_posicionamiento_zona:>18}")
    print(f"  {'Colapsos en Zonas de Recepción':<38} | {b.colapsos_zona_recepcion:>18} | {o.colapsos_zona_recepcion:>18}")
    print("  " + "-" * 80)
    print(
        f"  IMPACTO: Ahorro S/ {imp.ahorro_total_soles:.2f} (-{imp.reduccion_costo_pct:.1f}%) | "
        f"Puntualidad +{imp.mejora_puntualidad_pp:.1f} pp | "
        f"Exceso bloqueado: {imp.unidades_exceso_bloqueadas} uds."
    )


def _cmd_simulate(scenario_id: str | None) -> int:
    sim = SimulationService()
    results = (sim.run_scenario(scenario_id),) if scenario_id else sim.run_all_scenarios()
    for res in results:
        _render_simulation_result(res)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fasbit",
        description="FASBIT - Planificador Lógico y Funcional de Abastecimiento (Prolog + Python)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Verifica el motor SWI-Prolog y resume la base de conocimientos.")
    sub.add_parser("plan", help="Ejecuta la planificación óptima de entregas y muelles.")

    p_routes = sub.add_parser("routes", help="Calcula y clasifica rutas desde un origen hacia el almacén.")
    p_routes.add_argument("--origen", default="puerto_callao", help="ID del nodo de origen.")
    p_routes.add_argument("--salida", default="07:10", help="Hora de salida en formato HH:MM.")
    p_routes.add_argument("--plazo", default="08:20", help="Hora límite de entrega en formato HH:MM.")

    p_sim = sub.add_parser("simulate", help="Ejecuta escenarios simulados comparativos.")
    p_sim.add_argument("--scenario", default=None, help="ID específico de escenario (opcional).")

    p_serve = sub.add_parser("serve", help="Inicia la API REST y el Dashboard Web interactivo.")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host de escucha.")
    p_serve.add_argument("--port", type=int, default=8000, help="Puerto HTTP.")

    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in (None, "simulate"):
        scenario_arg = getattr(args, "scenario", None)
        return _cmd_simulate(scenario_arg)
    if args.command == "status":
        return _cmd_status()
    if args.command == "plan":
        return _cmd_plan()
    if args.command == "routes":
        return _cmd_routes(args.origen, args.salida, args.plazo)
    if args.command == "serve":
        uvicorn.run("fasbit.interfaces.api.app:app", host=args.host, port=args.port, reload=False)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

