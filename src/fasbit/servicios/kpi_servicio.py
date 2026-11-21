"""Consolidación funcional de indicadores clave (KPIs) con functools.reduce."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from functools import reduce
from types import MappingProxyType

from fasbit.modelos.entrega_modelo import (
    ACCIONES_OPERATIVAS,
    ESTADOS_ARRIBO,
    ESTADOS_CUMPLIMIENTO_SLA,
    EvaluacionEntrega,
)
from fasbit.servicios.multa_servicio import redondear_soles


@dataclass(frozen=True)
class AlertaLogica:
    """Alerta operativa derivada mediante cuantificadores de primer orden."""

    cuantificador: str
    mensaje: str
    activa: bool


@dataclass(frozen=True)
class ResumenKpi:
    """Resumen inmutable de métricas operativas y financieras del turno."""

    total_entregas: int
    total_cumplimiento_sla: int
    total_incidencias: int
    puntualidad_porcentaje: float
    total_multas_soles: float
    promedio_retraso_minutos: float
    conteo_por_estado: Mapping[str, int]
    conteo_por_accion: Mapping[str, int]
    alertas_turno: tuple[AlertaLogica, ...] = ()


@dataclass(frozen=True)
class _AcumuladorKpi:
    """Estado interno inmutable utilizado durante la reducción funcional."""

    total_entregas: int
    total_cumplimiento_sla: int
    total_incidencias: int
    suma_multas: Decimal
    total_presentados: int
    por_estado: Mapping[str, int]
    por_accion: Mapping[str, int]


def _acumular_retrasos_tupla(
    tupla: tuple[EvaluacionEntrega, ...],
    acumulado: int,
) -> int:
    """Paso de recursión de cola con acumulador explícito."""
    if not tupla:
        return acumulado
    cabeza, cola = tupla[0], tupla[1:]
    aporte = cabeza.minutos_retraso if cabeza.estado_arribo != "no_presentado" else 0
    return _acumular_retrasos_tupla(cola, acumulado + aporte)


def acumular_retrasos_cola(
    evaluaciones: Iterable[EvaluacionEntrega],
    acumulado: int = 0,
) -> int:
    """Suma minutos de retraso de unidades presentadas usando recursión de cola."""
    return _acumular_retrasos_tupla(tuple(evaluaciones), acumulado)


def verificar_alertas_turno(
    evaluaciones: Iterable[EvaluacionEntrega],
) -> tuple[AlertaLogica, ...]:
    """Evalúa propiedades operativas del turno mediante cuantificadores ∀ y ∃."""
    tupla = tuple(evaluaciones)
    cumplimientos = tuple(
        ev for ev in tupla if ev.estado_arribo in ESTADOS_CUMPLIMIENTO_SLA
    )
    consistencia_sla = all(ev.multa_soles == 0.0 for ev in cumplimientos)
    hay_critica_incidencia = any(
        ev.entrega.criticidad == "alta" and ev.es_incidencia for ev in tupla
    )
    hay_reprogramacion = any(
        ev.accion_operativa == "reprogramacion_urgente" for ev in tupla
    )

    return (
        AlertaLogica(
            cuantificador="∀",
            mensaje="Las entregas a tiempo tienen S/ 0.00 de multa.",
            activa=consistencia_sla,
        ),
        AlertaLogica(
            cuantificador="∃",
            mensaje="Hay entregas urgentes con retraso o que no vinieron.",
            activa=hay_critica_incidencia,
        ),
        AlertaLogica(
            cuantificador="∃",
            mensaje="Hay entregas que necesitan nueva hora urgente.",
            activa=hay_reprogramacion,
        ),
    )


def _crear_acumulador_inicial() -> _AcumuladorKpi:
    """Construye el acumulador inicial con ceros para todos los estados y acciones."""
    return _AcumuladorKpi(
        total_entregas=0,
        total_cumplimiento_sla=0,
        total_incidencias=0,
        suma_multas=Decimal("0.00"),
        total_presentados=0,
        por_estado=MappingProxyType({estado: 0 for estado in ESTADOS_ARRIBO}),
        por_accion=MappingProxyType({accion: 0 for accion in ACCIONES_OPERATIVAS}),
    )


def _acumular_evaluacion(
    acumulado: _AcumuladorKpi,
    evaluacion: EvaluacionEntrega,
) -> _AcumuladorKpi:
    """Paso puro de reducción que retorna un nuevo acumulador sin mutar el previo."""
    es_cumplimiento = evaluacion.estado_arribo in ESTADOS_CUMPLIMIENTO_SLA
    se_presento = evaluacion.estado_arribo != "no_presentado"

    nuevo_por_estado = {
        **dict(acumulado.por_estado),
        evaluacion.estado_arribo: acumulado.por_estado[evaluacion.estado_arribo] + 1,
    }
    nuevo_por_accion = {
        **dict(acumulado.por_accion),
        evaluacion.accion_operativa: (
            acumulado.por_accion[evaluacion.accion_operativa] + 1
        ),
    }

    return _AcumuladorKpi(
        total_entregas=acumulado.total_entregas + 1,
        total_cumplimiento_sla=acumulado.total_cumplimiento_sla
        + (1 if es_cumplimiento else 0),
        total_incidencias=acumulado.total_incidencias
        + (1 if evaluacion.es_incidencia else 0),
        suma_multas=acumulado.suma_multas + Decimal(str(evaluacion.multa_soles)),
        total_presentados=acumulado.total_presentados + (1 if se_presento else 0),
        por_estado=MappingProxyType(nuevo_por_estado),
        por_accion=MappingProxyType(nuevo_por_accion),
    )


def calcular_kpis_turno(
    evaluaciones: Iterable[EvaluacionEntrega],
) -> ResumenKpi:
    """Consolida KPIs con functools.reduce, recursión de cola y cuantificadores."""
    tupla = tuple(evaluaciones)
    final = reduce(_acumular_evaluacion, tupla, _crear_acumulador_inicial())
    suma_retraso_presentados = acumular_retrasos_cola(tupla)

    puntualidad = (
        round((final.total_cumplimiento_sla / final.total_entregas) * 100, 2)
        if final.total_entregas > 0
        else 0.0
    )
    promedio_retraso = (
        round(suma_retraso_presentados / final.total_presentados, 1)
        if final.total_presentados > 0
        else 0.0
    )

    return ResumenKpi(
        total_entregas=final.total_entregas,
        total_cumplimiento_sla=final.total_cumplimiento_sla,
        total_incidencias=final.total_incidencias,
        puntualidad_porcentaje=puntualidad,
        total_multas_soles=redondear_soles(final.suma_multas),
        promedio_retraso_minutos=promedio_retraso,
        conteo_por_estado=final.por_estado,
        conteo_por_accion=final.por_accion,
        alertas_turno=verificar_alertas_turno(tupla),
    )
