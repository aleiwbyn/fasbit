"""Pruebas unitarias para la consolidación funcional de KPIs del turno."""

from pathlib import Path

import pytest

from fasbit.modelos import (
    ACCIONES_OPERATIVAS,
    ESTADOS_ARRIBO,
    Entrega,
    Proveedor,
)
from fasbit.repositorios import cargar_entregas
from fasbit.servicios.kpi_servicio import (
    acumular_retrasos_cola,
    calcular_kpis_turno,
    verificar_alertas_turno,
)
from fasbit.servicios.multa_servicio import liquidar_entregas


def test_kpis_coleccion_vacia() -> None:
    kpis = calcular_kpis_turno(())

    assert kpis.total_entregas == 0
    assert kpis.total_cumplimiento_sla == 0
    assert kpis.total_incidencias == 0
    assert kpis.puntualidad_porcentaje == 0.0
    assert kpis.total_multas_soles == 0.0
    assert kpis.promedio_retraso_minutos == 0.0
    assert set(kpis.conteo_por_estado.keys()) == set(ESTADOS_ARRIBO)
    assert set(kpis.conteo_por_accion.keys()) == set(ACCIONES_OPERATIVAS)
    assert all(valor == 0 for valor in kpis.conteo_por_estado.values())
    assert [a.activa for a in kpis.alertas_turno] == [True, False, False]


def test_kpis_consolidacion_y_conteos_inmutables() -> None:
    proveedor = Proveedor("PROV-1", "Alicorp S.A.A.", "20100055237", 15, 4.0, 450.0)
    entregas = (
        Entrega("ENT-001", "OC-1", proveedor, "08:00", "07:55", "alta"),
        Entrega("ENT-002", "OC-2", proveedor, "08:00", "08:10", "media"),
        Entrega("ENT-003", "OC-3", proveedor, "08:00", "08:30", "alta"),
        Entrega("ENT-004", "OC-4", proveedor, "08:00", None, "baja", no_presentado=True),
    )
    evaluaciones = liquidar_entregas(entregas)
    kpis = calcular_kpis_turno(evaluaciones)

    assert kpis.total_entregas == 4
    assert kpis.total_cumplimiento_sla == 2
    assert kpis.total_incidencias == 2
    assert kpis.puntualidad_porcentaje == 50.0
    assert kpis.total_multas_soles == 510.0
    # Presentadas: retrasos 0, 10, 30 -> promedio 40 / 3 = 13.3 min
    assert kpis.promedio_retraso_minutos == 13.3
    assert kpis.conteo_por_estado["a_tiempo"] == 1
    assert kpis.conteo_por_estado["dentro_de_tolerancia"] == 1
    assert kpis.conteo_por_estado["retraso_leve"] == 1
    assert kpis.conteo_por_estado["retraso_grave"] == 0
    assert kpis.conteo_por_estado["no_presentado"] == 1
    assert kpis.conteo_por_accion["admision_prioritaria"] == 2
    assert kpis.conteo_por_accion["admision_estandar"] == 1
    assert kpis.conteo_por_accion["rechazo_o_cancelacion"] == 1

    with pytest.raises(TypeError):
        kpis.conteo_por_estado["a_tiempo"] = 99  # type: ignore[index]


def test_kpis_datos_semilla_del_turno() -> None:
    ruta_semilla = Path(__file__).resolve().parents[1] / "data" / "entregas.json"
    entregas = cargar_entregas(ruta_semilla)
    kpis = calcular_kpis_turno(liquidar_entregas(entregas))

    assert kpis.total_entregas == 10
    assert kpis.total_cumplimiento_sla == 4
    assert kpis.total_incidencias == 6
    assert kpis.puntualidad_porcentaje == 40.0
    assert kpis.total_multas_soles == 1069.5
    assert acumular_retrasos_cola(liquidar_entregas(entregas)) == 255

    alertas = verificar_alertas_turno(liquidar_entregas(entregas))
    assert len(alertas) == 3
    assert all(a.activa for a in alertas)
    assert kpis.alertas_turno == alertas
