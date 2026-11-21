"""Pruebas unitarias para el cálculo funcional de multas e inmutabilidad."""

from dataclasses import FrozenInstanceError

import pytest

from fasbit.modelos import Entrega, Proveedor
from fasbit.servicios.multa_servicio import (
    Resultado,
    calcular_multa_entrega,
    componer,
    crear_calculador_multa,
    evaluar_entrega,
    evaluar_entrega_segura,
    extraer_multas_soles,
    liquidar_entregas,
    obtener_multa_de_entrega,
    redondear_soles,
)


def _crear_proveedor() -> Proveedor:
    return Proveedor(
        id_proveedor="PROV-T1",
        nombre="Alicorp S.A.A.",
        ruc="20100055237",
        tolerancia_minutos=15,
        tarifa_minuto_soles=4.5,
        penalidad_inasistencia_soles=450.0,
    )


def _crear_entrega(
    id_entrega: str,
    hora_cita: str,
    hora_llegada: str | None,
    criticidad: str = "alta",
    no_presentado: bool = False,
) -> Entrega:
    return Entrega(
        id_entrega=id_entrega,
        codigo_orden=f"OC-{id_entrega}",
        proveedor=_crear_proveedor(),
        hora_cita=hora_cita,
        hora_llegada=hora_llegada,
        criticidad=criticidad,
        no_presentado=no_presentado,
    )


def test_redondeo_soles_round_half_up() -> None:
    assert redondear_soles(1.005) == 1.01
    assert redondear_soles(12.345) == 12.35
    assert redondear_soles(10.0) == 10.0


def test_calcular_multas_por_estado() -> None:
    entrega = _crear_entrega("ENT-1", "08:00", "08:00")
    assert calcular_multa_entrega(entrega, "a_tiempo", 0) == 0.0
    assert calcular_multa_entrega(entrega, "dentro_de_tolerancia", 0) == 0.0
    assert calcular_multa_entrega(entrega, "retraso_leve", 12) == 54.0
    assert calcular_multa_entrega(entrega, "retraso_grave", 45) == 202.5
    assert calcular_multa_entrega(entrega, "no_presentado", 0) == 450.0

    with pytest.raises(ValueError):
        calcular_multa_entrega(entrega, "invalido", 5)


def test_liquidar_entregas_y_extraer_multas() -> None:
    entregas = (
        _crear_entrega("ENT-001", "08:00", "07:55", "alta"),
        _crear_entrega("ENT-002", "08:00", "08:10", "media"),
        _crear_entrega("ENT-003", "08:00", "08:30", "alta"),
        _crear_entrega("ENT-004", "08:00", "09:00", "baja"),
        _crear_entrega("ENT-005", "08:00", None, "media", no_presentado=True),
    )
    copia_original = tuple(entregas)

    evaluaciones = liquidar_entregas(entregas)

    assert entregas == copia_original
    assert len(evaluaciones) == 5
    assert extraer_multas_soles(evaluaciones) == (0.0, 0.0, 67.5, 202.5, 450.0)
    assert evaluaciones[2].estado_arribo == "retraso_leve"
    assert evaluaciones[3].accion_operativa == "rechazo_o_cancelacion"
    assert evaluaciones[4].es_incidencia is True


def test_modelos_son_inmutables() -> None:
    entrega = _crear_entrega("ENT-099", "09:00", "09:00")
    evaluacion = evaluar_entrega(entrega)

    with pytest.raises(FrozenInstanceError):
        entrega.criticidad = "baja"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        entrega.proveedor.tolerancia_minutos = 99  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        evaluacion.multa_soles = 999.0  # type: ignore[misc]


def test_currificacion_composicion_y_functor_resultado() -> None:
    calculador_alicorp = crear_calculador_multa(4.5)
    assert calculador_alicorp(0) == 0.0
    assert calculador_alicorp(12) == 54.0

    doble_mas_uno = componer(lambda x: x + 1, lambda x: x * 2)
    assert doble_mas_uno(5) == 11

    entrega_valida = _crear_entrega("ENT-100", "08:00", "08:25", "alta")
    assert obtener_multa_de_entrega(entrega_valida) == 45.0

    # Ley de identidad del Functor: fmap(id) == id
    def identidad(x: int) -> int:
        return x

    envuelto = Resultado(valor=10)
    assert envuelto.fmap(identidad) == envuelto

    # Ley de composición del Functor: fmap(g o f) == fmap(f).fmap(g)
    def f(x: int) -> int:
        return x + 3

    def g(x: int) -> int:
        return x * 2

    assert envuelto.fmap(componer(g, f)) == envuelto.fmap(f).fmap(g)

    segura_ok = evaluar_entrega_segura(entrega_valida)
    assert segura_ok.es_valido is True
    assert segura_ok.fmap(lambda ev: ev.multa_soles).valor == 45.0

    entrega_mala = _crear_entrega("ENT-ERR", "99:99", "08:00", "alta")
    segura_err = evaluar_entrega_segura(entrega_mala)
    assert segura_err.es_valido is False
    assert segura_err.error is not None
    propagada = segura_err.fmap(lambda ev: ev.multa_soles)
    assert propagada.es_valido is False
    assert propagada.error == segura_err.error
