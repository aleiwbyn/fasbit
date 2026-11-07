"""
Pipelines funcionales, combinadores de orden superior y transformadores puros.
Convierte estructuras crudas provenientes de Prolog en entidades inmutables.
"""

from __future__ import annotations

from functools import reduce
from typing import Any, Callable, Iterable, TypeVar

from fasbit.domain.models import (
    BaselineTaskEvaluation,
    PlannedTask,
    RoadSegmentStep,
    RouteEvaluation,
    minutes_to_hhmm,
)

T = TypeVar("T")


def pipe(initial_value: Any, *functions: Callable[[Any], Any]) -> Any:
    """Aplica secuencialmente una serie de funciones puras de izquierda a derecha."""
    return reduce(lambda acc, fn: fn(acc), functions, initial_value)


def compose(*functions: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Compone funciones puras (f o g)(x) = f(g(x))."""
    return lambda value: reduce(lambda acc, fn: fn(acc), reversed(functions), value)


def parse_segment(raw: dict[str, Any]) -> RoadSegmentStep:
    """Transforma un diccionario de tramo en un RoadSegmentStep inmutable."""
    return RoadSegmentStep(
        origen=str(raw["origen"]),
        destino=str(raw["destino"]),
        distancia_km=float(raw["distancia_km"]),
        tiempo_base_min=float(raw["tiempo_base_min"]),
        tiempo_real_min=float(raw["tiempo_real_min"]),
        costo_soles=float(raw["costo_soles"]),
        trafico=str(raw["trafico"]),
    )


def parse_route_evaluation(raw: dict[str, Any]) -> RouteEvaluation:
    """Transforma un diccionario de ruta en una entidad RouteEvaluation inmutable."""
    return RouteEvaluation(
        nodos=tuple(str(n) for n in raw["nodos"]),
        tramos=tuple(map(parse_segment, raw.get("tramos", ()))),
        distancia_km=float(raw["distancia_km"]),
        tiempo_transito_min=float(raw["tiempo_transito_min"]),
        hora_salida_min=float(raw["hora_salida_min"]),
        hora_llegada_min=float(raw["hora_llegada_min"]),
        estado_puntualidad=str(raw["estado_puntualidad"]),
        minutos_retraso=float(raw["minutos_retraso"]),
        minutos_espera_ventana=float(raw["minutos_espera_ventana"]),
        costo_transporte_soles=float(raw["costo_transporte_soles"]),
        costo_multa_soles=float(raw["costo_multa_soles"]),
        costo_total_ruta_soles=float(raw["costo_total_ruta_soles"]),
        puntaje_optimizacion=float(raw.get("puntaje_optimizacion", 0.0)),
    )


def parse_planned_task(raw: dict[str, Any]) -> PlannedTask:
    """Transforma una tarea planificada cruda en un PlannedTask inmutable."""
    return PlannedTask(
        id_pedido=str(raw["id_pedido"]),
        id_proveedor=str(raw["id_proveedor"]),
        nombre_proveedor=str(raw["nombre_proveedor"]),
        origen=str(raw["origen"]),
        categoria=str(raw["categoria"]),
        prioridad_stock=int(raw["prioridad_stock"]),
        estado_stock_previo=str(raw["estado_stock_previo"]),
        stock_antes=int(raw["stock_antes"]),
        stock_despues=int(raw["stock_despues"]),
        cantidad_solicitada=int(raw["cantidad_solicitada"]),
        cantidad_aceptada=int(raw["cantidad_aceptada"]),
        unidades_exceso_evitadas=int(raw["unidades_exceso_evitadas"]),
        decision_almacen=str(raw["decision_almacen"]),
        volumen_efectivo_m3=float(raw["volumen_efectivo_m3"]),
        ventana_inicio_min=float(raw["ventana_inicio_min"]),
        plazo_maximo_min=float(raw["plazo_maximo_min"]),
        zona_habitual_proveedor=str(raw["zona_habitual_proveedor"]),
        zona_asignada=str(raw["zona_asignada"]),
        nombre_zona_asignada=str(raw["nombre_zona_asignada"]),
        accion_zona=str(raw["accion_zona"]),
        inicio_descarga_min=float(raw["inicio_descarga_min"]),
        fin_descarga_min=float(raw["fin_descarga_min"]),
        espera_muelle_min=float(raw["espera_muelle_min"]),
        rutas_evaluadas=int(raw["rutas_evaluadas"]),
        ruta=parse_route_evaluation(raw["ruta"]),
        costo_sobrealmacenamiento_soles=float(raw["costo_sobrealmacenamiento_soles"]),
        costo_operativo_total_soles=float(raw["costo_operativo_total_soles"]),
    )


def parse_baseline_task(raw: dict[str, Any]) -> BaselineTaskEvaluation:
    """Transforma una evaluación habitual cruda en un BaselineTaskEvaluation inmutable."""
    return BaselineTaskEvaluation(
        id_pedido=str(raw["id_pedido"]),
        id_proveedor=str(raw["id_proveedor"]),
        nombre_proveedor=str(raw["nombre_proveedor"]),
        origen=str(raw["origen"]),
        categoria=str(raw["categoria"]),
        cantidad_solicitada=int(raw["cantidad_solicitada"]),
        unidades_exceso_almacen=int(raw["unidades_exceso_almacen"]),
        ventana_inicio_min=float(raw["ventana_inicio_min"]),
        plazo_maximo_min=float(raw["plazo_maximo_min"]),
        zona_intentada=str(raw["zona_intentada"]),
        nombre_zona_intentada=str(raw["nombre_zona_intentada"]),
        error_posicionamiento_zona=bool(raw["error_posicionamiento_zona"]),
        colapso_zona_recepcion=bool(raw["colapso_zona_recepcion"]),
        inicio_recepcion_min=float(raw["inicio_recepcion_min"]),
        fin_recepcion_min=float(raw["fin_recepcion_min"]),
        ruta=parse_route_evaluation(raw["ruta"]),
        costo_reproceso_zona_soles=float(raw["costo_reproceso_zona_soles"]),
        costo_congestion_muelle_soles=float(raw["costo_congestion_muelle_soles"]),
        costo_sobrealmacenamiento_soles=float(raw["costo_sobrealmacenamiento_soles"]),
        costo_operativo_total_soles=float(raw["costo_operativo_total_soles"]),
    )


def build_dock_schedule_timeline(tasks: Iterable[PlannedTask]) -> tuple[dict[str, Any], ...]:
    """
    Construye funcionalmente la línea de tiempo ordenada de ocupación de muelles,
    filtrando entregas que no requirieron descarga.
    """
    active_tasks = filter(lambda t: t.zona_asignada != "sin_descarga", tasks)
    sorted_tasks = sorted(active_tasks, key=lambda t: (t.zona_asignada, t.inicio_descarga_min))
    return tuple(
        map(
            lambda t: {
                "zona_id": t.zona_asignada,
                "zona_nombre": t.nombre_zona_asignada,
                "id_pedido": t.id_pedido,
                "proveedor": t.nombre_proveedor,
                "categoria": t.categoria,
                "cantidad_aceptada": t.cantidad_aceptada,
                "inicio_min": t.inicio_descarga_min,
                "fin_min": t.fin_descarga_min,
                "ventana_hhmm": f"{minutes_to_hhmm(t.inicio_descarga_min)} - {minutes_to_hhmm(t.fin_descarga_min)}",
                "accion_zona": t.accion_zona,
            },
            sorted_tasks,
        )
    )

