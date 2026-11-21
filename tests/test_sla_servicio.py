"""Pruebas unitarias para las reglas declarativas SLA y clasificación de arribos."""

import pytest

from fasbit.modelos import ACCIONES_OPERATIVAS, CRITICIDADES_VALIDAS, ESTADOS_ARRIBO
from fasbit.servicios.sla_servicio import (
    INTERVALO_A_TIEMPO,
    INTERVALO_RETRASO_GRAVE,
    INTERVALO_RETRASO_LEVE,
    UMBRAL_RETRASO_LEVE_MINUTOS,
    IntervaloMinutos,
    calcular_minutos_exceso,
    calcular_minutos_retraso,
    clasificar_estado_arribo,
    determinar_accion_operativa,
    es_cumplimiento_sla,
    es_incidencia_sla,
    explicar_regla_operativa,
    fuera_de_intervalo,
    parsear_hora_a_minutos,
    pertenece_intervalo,
    sugerir_ventanas_reprogramacion,
)


@pytest.mark.parametrize(
    ("hora_texto", "esperado"),
    [
        ("00:00", 0),
        ("07:30", 450),
        ("12:05", 725),
        ("23:59", 1439),
    ],
)
def test_parsear_hora_a_minutos_valida(hora_texto: str, esperado: int) -> None:
    assert parsear_hora_a_minutos(hora_texto) == esperado


@pytest.mark.parametrize(
    "hora_invalida",
    ["", "8:00", "24:00", "12:60", "12-30", "ab:cd", "08:5"],
)
def test_parsear_hora_a_minutos_invalida(hora_invalida: str) -> None:
    with pytest.raises(ValueError):
        parsear_hora_a_minutos(hora_invalida)


def test_calcular_minutos_retraso_y_exceso() -> None:
    assert calcular_minutos_retraso("08:00", "07:45") == 0
    assert calcular_minutos_retraso("08:00", "08:00") == 0
    assert calcular_minutos_retraso("08:00", "08:25") == 25
    assert calcular_minutos_retraso("08:00", None, no_presentado=True) == 0

    assert calcular_minutos_exceso(10, 15) == 0
    assert calcular_minutos_exceso(15, 15) == 0
    assert calcular_minutos_exceso(25, 15) == 10
    assert calcular_minutos_exceso(10, -5) == 10


def test_clasificar_estado_arribo_y_frontera_30_minutos() -> None:
    assert UMBRAL_RETRASO_LEVE_MINUTOS == 30
    assert clasificar_estado_arribo("08:00", "07:50", 15) == "a_tiempo"
    assert clasificar_estado_arribo("08:00", "08:00", 15) == "a_tiempo"
    assert clasificar_estado_arribo("08:00", "08:15", 15) == "dentro_de_tolerancia"
    assert clasificar_estado_arribo("08:00", "08:45", 15) == "retraso_leve"
    assert clasificar_estado_arribo("08:00", "08:46", 15) == "retraso_grave"
    assert (
        clasificar_estado_arribo("08:00", None, 15, no_presentado=True)
        == "no_presentado"
    )


@pytest.mark.parametrize(
    ("estado", "criticidad", "accion_esperada"),
    [
        ("a_tiempo", "alta", "admision_prioritaria"),
        ("a_tiempo", "media", "admision_estandar"),
        ("a_tiempo", "baja", "admision_estandar"),
        ("dentro_de_tolerancia", "alta", "admision_prioritaria"),
        ("dentro_de_tolerancia", "media", "admision_estandar"),
        ("dentro_de_tolerancia", "baja", "admision_estandar"),
        ("retraso_leve", "alta", "admision_prioritaria"),
        ("retraso_leve", "media", "admision_estandar"),
        ("retraso_leve", "baja", "recepcion_fin_turno"),
        ("retraso_grave", "alta", "reprogramacion_urgente"),
        ("retraso_grave", "media", "recepcion_fin_turno"),
        ("retraso_grave", "baja", "rechazo_o_cancelacion"),
        ("no_presentado", "alta", "reprogramacion_urgente"),
        ("no_presentado", "media", "rechazo_o_cancelacion"),
        ("no_presentado", "baja", "rechazo_o_cancelacion"),
    ],
)
def test_matriz_completa_15_combinaciones(
    estado: str, criticidad: str, accion_esperada: str
) -> None:
    accion = determinar_accion_operativa(estado, criticidad)
    assert accion == accion_esperada
    assert accion in ACCIONES_OPERATIVAS
    explicacion = explicar_regla_operativa(estado, criticidad, accion)
    assert criticidad in explicacion


def test_errores_y_marca_de_incidencia() -> None:
    assert len(ESTADOS_ARRIBO) == 5
    assert CRITICIDADES_VALIDAS == ("alta", "media", "baja")

    with pytest.raises(ValueError):
        determinar_accion_operativa("desconocido", "alta")
    with pytest.raises(ValueError):
        determinar_accion_operativa("a_tiempo", "p1")
    with pytest.raises(ValueError):
        explicar_regla_operativa("a_tiempo", "alta", "accion_invalida")

    assert es_incidencia_sla("a_tiempo") is False
    assert es_incidencia_sla("dentro_de_tolerancia") is False
    assert es_incidencia_sla("retraso_leve") is True
    assert es_incidencia_sla("retraso_grave") is True
    assert es_incidencia_sla("no_presentado") is True


def test_intervalos_y_memoizacion_lru_cache() -> None:
    personalizado = IntervaloMinutos(10, 20, "ventana")
    assert pertenece_intervalo(10, personalizado) is True
    assert pertenece_intervalo(20, personalizado) is True
    assert fuera_de_intervalo(21, personalizado) is True

    assert pertenece_intervalo(0, INTERVALO_A_TIEMPO) is True
    assert pertenece_intervalo(30, INTERVALO_RETRASO_LEVE) is True
    assert pertenece_intervalo(31, INTERVALO_RETRASO_GRAVE) is True
    assert fuera_de_intervalo(30, INTERVALO_RETRASO_GRAVE) is True

    parsear_hora_a_minutos.cache_clear()
    determinar_accion_operativa.cache_clear()
    assert parsear_hora_a_minutos("07:45") == 465
    assert parsear_hora_a_minutos("07:45") == 465
    assert parsear_hora_a_minutos.cache_info().hits >= 1

    assert determinar_accion_operativa("a_tiempo", "alta") == "admision_prioritaria"
    assert determinar_accion_operativa("a_tiempo", "alta") == "admision_prioritaria"
    assert determinar_accion_operativa.cache_info().hits >= 1


def test_negacion_cumplimiento_y_ventanas_perezosas() -> None:
    assert es_cumplimiento_sla("a_tiempo") is True
    assert es_cumplimiento_sla("dentro_de_tolerancia") is True
    assert es_cumplimiento_sla("retraso_leve") is False
    assert es_cumplimiento_sla("no_presentado") is False
    assert es_cumplimiento_sla("desconocido") is False

    assert sugerir_ventanas_reprogramacion("10:55", paso_minutos=15, cantidad=4) == (
        "11:10",
        "11:25",
        "11:40",
        "11:55",
    )
    assert sugerir_ventanas_reprogramacion("23:45", paso_minutos=15, cantidad=2) == (
        "00:00",
        "00:15",
    )
    assert sugerir_ventanas_reprogramacion("10:00", cantidad=0) == ()

    with pytest.raises(ValueError):
        sugerir_ventanas_reprogramacion("10:00", paso_minutos=0)
