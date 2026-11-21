"""Controlador operativo de recepción logística, evaluación SLA y KPIs."""

from typing import Any

from flask import Blueprint, current_app, redirect, render_template, request, url_for

from fasbit.controladores.auth_controlador import requiere_rol, requiere_sesion
from fasbit.modelos.entrega_modelo import Entrega
from fasbit.repositorios.entrega_repositorio import cargar_entregas, guardar_entregas
from fasbit.servicios.entrega_servicio import (
    actualizar_llegada_entrega,
    agregar_entrega_a_coleccion,
    buscar_entrega_por_id,
    crear_entrega,
    eliminar_entrega_en_coleccion,
    filtrar_evaluaciones,
    obtener_proveedores_unicos,
    ordenar_evaluaciones,
    reemplazar_entrega_en_coleccion,
)
from fasbit.servicios.kpi_servicio import calcular_kpis_turno
from fasbit.servicios.multa_servicio import evaluar_entrega_segura, liquidar_entregas
from fasbit.servicios.sla_servicio import sugerir_ventanas_reprogramacion

recepcion_bp = Blueprint("recepcion", __name__)


def _leer_filtros() -> dict[str, str]:
    """Extrae los parámetros activos de filtrado y ordenamiento."""
    ordenar_por = request.values.get("ordenar_por", "cita").strip() or "cita"
    direccion = request.values.get("direccion", "asc").strip().lower()
    if direccion not in ("asc", "desc"):
        direccion = "asc"
    return {
        "estado": request.values.get("estado", "").strip(),
        "criticidad": request.values.get("criticidad", "").strip(),
        "accion": request.values.get("accion", "").strip(),
        "buscar": request.values.get("buscar", "").strip(),
        "ordenar_por": ordenar_por,
        "direccion": direccion,
    }


def _construir_datos_panel(
    entregas: tuple[Entrega, ...],
    filtros: dict[str, str],
) -> dict[str, Any]:
    """Evalúa las entregas del turno y prepara KPIs, tabla filtrada y proveedores."""
    evaluaciones_turno = liquidar_entregas(entregas)
    kpis = calcular_kpis_turno(evaluaciones_turno)
    filtradas = filtrar_evaluaciones(
        evaluaciones_turno,
        estado=filtros["estado"],
        criticidad=filtros["criticidad"],
        accion=filtros["accion"],
        texto_busqueda=filtros["buscar"],
    )
    ordenadas = ordenar_evaluaciones(
        filtradas,
        criterio=filtros["ordenar_por"],
        descendente=(filtros["direccion"] == "desc"),
    )
    return {
        "entregas": entregas,
        "evaluaciones": ordenadas,
        "kpis": kpis,
        "proveedores": obtener_proveedores_unicos(entregas),
        "filtros": filtros,
    }


@recepcion_bp.get("/recepcion")
@requiere_sesion
def panel() -> str:
    """Vista principal del control de recepción del turno."""
    entregas = cargar_entregas(current_app.config["RUTA_ENTREGAS"])
    filtros = _leer_filtros()
    contexto = _construir_datos_panel(entregas, filtros)
    return render_template("recepcion.html", **contexto)


@recepcion_bp.get("/recepcion/tabla")
@requiere_sesion
def tabla_parcial() -> str:
    """Devuelve únicamente el parcial de la tabla filtrada y ordenada."""
    entregas = cargar_entregas(current_app.config["RUTA_ENTREGAS"])
    filtros = _leer_filtros()
    contexto = _construir_datos_panel(entregas, filtros)
    return render_template(
        "parciales/_tabla_entregas.html",
        evaluaciones=contexto["evaluaciones"],
        filtros=filtros,
        oob=False,
    )


@recepcion_bp.get("/recepcion/kpis")
@requiere_sesion
def kpis_parcial() -> str:
    """Devuelve únicamente el parcial de tarjetas KPI del turno."""
    entregas = cargar_entregas(current_app.config["RUTA_ENTREGAS"])
    evaluaciones_turno = liquidar_entregas(entregas)
    kpis = calcular_kpis_turno(evaluaciones_turno)
    return render_template("parciales/_tarjetas_kpi.html", kpis=kpis, oob=False)


def _resolver_entrega_evaluada(
    entregas: tuple[Entrega, ...],
) -> tuple[Entrega, tuple[Entrega, ...]]:
    """Construye la entrega actualizada o nueva a partir del formulario recibido."""
    tipo_operacion = request.form.get("tipo_operacion", "existente").strip()
    no_presentado = request.form.get("no_presentado") in ("1", "true", "on", "si")
    hora_llegada = request.form.get("hora_llegada", "").strip() or None
    observacion = request.form.get("observacion", "")

    if tipo_operacion == "nueva":
        id_proveedor = request.form.get("id_proveedor", "").strip()
        proveedores = obtener_proveedores_unicos(entregas)
        proveedor = next(
            filter(lambda item: item.id_proveedor == id_proveedor, proveedores),
            None,
        )
        if proveedor is None:
            raise ValueError("Elige una empresa de la lista.")

        nueva = crear_entrega(
            entregas_existentes=entregas,
            codigo_orden=request.form.get("codigo_orden", ""),
            proveedor=proveedor,
            hora_cita=request.form.get("hora_cita", ""),
            hora_llegada=hora_llegada,
            criticidad=request.form.get("criticidad", ""),
            no_presentado=no_presentado,
            observacion=observacion,
        )
        return nueva, agregar_entrega_a_coleccion(entregas, nueva)

    id_entrega = request.form.get("id_entrega", "").strip()
    entrega_actual = buscar_entrega_por_id(entregas, id_entrega)
    if entrega_actual is None:
        raise ValueError("Elige una entrega de la lista.")

    actualizada = actualizar_llegada_entrega(
        entrega_actual,
        hora_llegada=hora_llegada,
        no_presentado=no_presentado,
        observacion=observacion,
    )
    return actualizada, reemplazar_entrega_en_coleccion(entregas, actualizada)


@recepcion_bp.post("/recepcion/evaluar")
@requiere_sesion
def evaluar() -> Any:
    """Evalúa o simula una llegada SLA y actualiza KPIs y tabla vía HTMX OOB."""
    ruta_entregas = current_app.config["RUTA_ENTREGAS"]
    entregas = cargar_entregas(ruta_entregas)
    filtros = _leer_filtros()
    modo = request.form.get("modo", "guardar").strip().lower()
    if modo not in ("guardar", "simular"):
        modo = "guardar"
    es_htmx = request.headers.get("HX-Request") == "true"

    try:
        entrega_objetivo, entregas_nuevas = _resolver_entrega_evaluada(entregas)
        resultado = evaluar_entrega_segura(entrega_objetivo)
        if not resultado.es_valido or resultado.valor is None:
            raise ValueError(resultado.error or "No se pudo revisar la entrega.")
        evaluacion = resultado.valor
        if modo == "guardar":
            guardar_entregas(ruta_entregas, entregas_nuevas)
            entregas_para_panel = entregas_nuevas
        else:
            entregas_para_panel = entregas
    except ValueError as exc:
        if es_htmx:
            return render_template(
                "parciales/_resultado_evaluacion.html",
                evaluacion=None,
                modo=modo,
                error=str(exc),
                incluir_oob=False,
            )
        contexto = _construir_datos_panel(entregas, filtros)
        contexto["error_evaluacion"] = str(exc)
        return render_template("recepcion.html", **contexto), 400

    contexto = _construir_datos_panel(entregas_para_panel, filtros)
    hora_base = evaluacion.entrega.hora_llegada or evaluacion.entrega.hora_cita
    ventanas_sugeridas = (
        sugerir_ventanas_reprogramacion(hora_base)
        if evaluacion.accion_operativa == "reprogramacion_urgente"
        else ()
    )

    if es_htmx:
        return render_template(
            "parciales/_resultado_evaluacion.html",
            evaluacion=evaluacion,
            modo=modo,
            error=None,
            ventanas_sugeridas=ventanas_sugeridas,
            incluir_oob=(modo == "guardar"),
            kpis=contexto["kpis"],
            evaluaciones=contexto["evaluaciones"],
            filtros=filtros,
        )

    contexto["evaluacion_resultado"] = evaluacion
    contexto["modo_resultado"] = modo
    contexto["ventanas_sugeridas"] = ventanas_sugeridas
    return render_template("recepcion.html", **contexto)


@recepcion_bp.post("/recepcion/entregas/<id_entrega>/eliminar")
@requiere_sesion
@requiere_rol("admin")
def eliminar_entrega(id_entrega: str) -> Any:
    """Elimina una entrega del turno (exclusivo admin) y actualiza tabla/KPIs."""
    ruta_entregas = current_app.config["RUTA_ENTREGAS"]
    entregas = cargar_entregas(ruta_entregas)
    filtros = _leer_filtros()
    es_htmx = request.headers.get("HX-Request") == "true"

    try:
        actualizadas = eliminar_entrega_en_coleccion(entregas, id_entrega)
        guardar_entregas(ruta_entregas, actualizadas)
    except ValueError as exc:
        if es_htmx:
            contexto = _construir_datos_panel(entregas, filtros)
            return render_template(
                "parciales/_tabla_entregas.html",
                evaluaciones=contexto["evaluaciones"],
                filtros=filtros,
                error_tabla=str(exc),
                oob=False,
            )
        return redirect(url_for("recepcion.panel"))

    if es_htmx:
        contexto = _construir_datos_panel(actualizadas, filtros)
        tabla_html = render_template(
            "parciales/_tabla_entregas.html",
            evaluaciones=contexto["evaluaciones"],
            filtros=filtros,
            mensaje_tabla=f"Se eliminó la entrega {id_entrega}.",
            oob=False,
        )
        kpis_html = render_template(
            "parciales/_tarjetas_kpi.html",
            kpis=contexto["kpis"],
            oob=True,
        )
        return f"{tabla_html}\n{kpis_html}"

    return redirect(url_for("recepcion.panel"))
