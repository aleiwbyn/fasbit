"""Pruebas unitarias para filtros, ordenamiento y mutabilidad nula de entregas."""

import pytest

from fasbit.modelos import Entrega, Proveedor
from fasbit.servicios.entrega_servicio import (
    actualizar_llegada_entrega,
    agregar_entrega_a_coleccion,
    buscar_entrega_por_id,
    crear_entrega,
    eliminar_entrega_en_coleccion,
    filtrar_evaluaciones,
    normalizar_codigo_orden,
    obtener_proveedores_unicos,
    ordenar_evaluaciones,
    reemplazar_entrega_en_coleccion,
)
from fasbit.servicios.multa_servicio import liquidar_entregas


def _entregas_prueba() -> tuple[Entrega, ...]:
    prov_a = Proveedor("PROV-1", "Alicorp S.A.A.", "20100055237", 15, 4.0, 400.0)
    prov_b = Proveedor("PROV-2", "Leche Gloria S.A.", "20100190797", 10, 5.0, 500.0)
    return (
        Entrega("ENT-001", "OC-101", prov_b, "10:00", "10:00", "media"),
        Entrega("ENT-002", "OC-102", prov_a, "08:00", "08:30", "alta"),
        Entrega("ENT-003", "OC-103", prov_a, "09:00", None, "baja", no_presentado=True),
    )


def test_filtrar_evaluaciones_individual_y_combinado() -> None:
    evaluaciones = liquidar_entregas(_entregas_prueba())

    assert len(filtrar_evaluaciones(evaluaciones, estado="a_tiempo")) == 1
    assert len(filtrar_evaluaciones(evaluaciones, criticidad="alta")) == 1
    assert len(filtrar_evaluaciones(evaluaciones, accion="rechazo_o_cancelacion")) == 1
    assert len(filtrar_evaluaciones(evaluaciones, texto_busqueda="alicorp")) == 2
    assert len(filtrar_evaluaciones(evaluaciones, texto_busqueda="20100190797")) == 1
    assert (
        len(
            filtrar_evaluaciones(
                evaluaciones,
                estado="retraso_leve",
                criticidad="alta",
                texto_busqueda="oc-102",
            )
        )
        == 1
    )


def test_ordenar_evaluaciones_por_todos_los_criterios() -> None:
    evaluaciones = liquidar_entregas(_entregas_prueba())

    por_cita = ordenar_evaluaciones(evaluaciones, criterio="cita")
    assert [ev.entrega.id_entrega for ev in por_cita] == [
        "ENT-002",
        "ENT-003",
        "ENT-001",
    ]

    por_retraso_desc = ordenar_evaluaciones(
        evaluaciones, criterio="retraso", descendente=True
    )
    assert por_retraso_desc[0].entrega.id_entrega == "ENT-002"

    por_multa_desc = ordenar_evaluaciones(
        evaluaciones, criterio="multa", descendente=True
    )
    assert [ev.multa_soles for ev in por_multa_desc] == [400.0, 60.0, 0.0]

    por_criticidad = ordenar_evaluaciones(evaluaciones, criterio="criticidad")
    assert [ev.entrega.criticidad for ev in por_criticidad] == [
        "alta",
        "media",
        "baja",
    ]

    por_proveedor = ordenar_evaluaciones(evaluaciones, criterio="proveedor")
    assert por_proveedor[0].entrega.proveedor.nombre == "Alicorp S.A.A."
    assert por_proveedor[-1].entrega.proveedor.nombre == "Leche Gloria S.A."


def test_actualizar_crear_y_reemplazar_sin_mutar_original() -> None:
    entregas = _entregas_prueba()
    encontrada = buscar_entrega_por_id(entregas, "ENT-001")
    assert encontrada is not None
    assert buscar_entrega_por_id(entregas, "ENT-999") is None

    actualizada = actualizar_llegada_entrega(
        encontrada,
        hora_llegada="10:25",
        no_presentado=False,
        observacion="Llegó con demora",
    )
    assert encontrada.hora_llegada == "10:00"
    assert actualizada.hora_llegada == "10:25"

    ausente = actualizar_llegada_entrega(encontrada, None, True, "No vino")
    assert ausente.no_presentado is True
    assert ausente.hora_llegada is None

    with pytest.raises(ValueError):
        actualizar_llegada_entrega(encontrada, "", False)

    proveedores = obtener_proveedores_unicos(entregas)
    assert [p.id_proveedor for p in proveedores] == ["PROV-1", "PROV-2"]

    nueva = crear_entrega(
        entregas,
        codigo_orden="OC-104",
        proveedor=proveedores[0],
        hora_cita="11:00",
        hora_llegada="11:05",
        criticidad="media",
    )
    assert nueva.id_entrega == "ENT-004"

    con_reemplazo = reemplazar_entrega_en_coleccion(entregas, actualizada)
    assert con_reemplazo[0].hora_llegada == "10:25"
    assert entregas[0].hora_llegada == "10:00"

    con_agregada = agregar_entrega_a_coleccion(entregas, nueva)
    assert len(con_agregada) == 4
    assert len(entregas) == 3

    with pytest.raises(ValueError):
        crear_entrega(entregas, "", proveedores[0], "11:00", "11:05", "alta")
    with pytest.raises(ValueError):
        crear_entrega(entregas, "OC-105", proveedores[0], "11:00", "11:05", "p1")

    assert normalizar_codigo_orden("") == ""
    assert normalizar_codigo_orden("  oc - 2026 ") == "OC-2026"

    restantes = eliminar_entrega_en_coleccion(entregas, "ENT-002")
    assert [e.id_entrega for e in restantes] == ["ENT-001", "ENT-003"]
    assert len(entregas) == 3

    with pytest.raises(ValueError):
        eliminar_entrega_en_coleccion(entregas, "ENT-999")
