"""Cálculo funcional puro de multas en soles y evaluación completa de entregas."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Generic, TypeVar

from fasbit.modelos.entrega_modelo import (
    ESTADO_PENDIENTE,
    ESTADOS_ARRIBO,
    ESTADOS_CUMPLIMIENTO_SLA,
    Entrega,
    EvaluacionEntrega,
)
from fasbit.servicios.sla_servicio import (
    calcular_minutos_exceso,
    calcular_minutos_retraso,
    clasificar_estado_arribo,
    determinar_accion_operativa,
    es_incidencia_sla,
    explicar_regla_operativa,
)

A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")
T = TypeVar("T")


@dataclass(frozen=True)
class Resultado(Generic[T]):
    """Functor inmutable para encadenar cálculos seguros sin excepciones."""

    valor: T | None = None
    error: str | None = None

    @property
    def es_valido(self) -> bool:
        """Indica si el contenedor almacena un valor válido sin errores."""
        return self.error is None and self.valor is not None

    def fmap(self, funcion: Callable[[T], B]) -> "Resultado[B]":
        """Aplica una función pura sobre el valor contenido preservando errores."""
        if not self.es_valido or self.valor is None:
            return Resultado(valor=None, error=self.error)
        try:
            return Resultado(valor=funcion(self.valor), error=None)
        except (TypeError, ValueError) as exc:
            return Resultado(valor=None, error=str(exc))


def componer(
    funcion_externa: Callable[[B], C],
    funcion_interna: Callable[[A], B],
) -> Callable[[A], C]:
    """Compone dos funciones puras cumpliendo (f o g)(x) = f(g(x))."""

    def compuesta(valor: A) -> C:
        return funcion_externa(funcion_interna(valor))

    return compuesta


def redondear_soles(monto: float | Decimal) -> float:
    """Redondea un monto monetario a dos decimales usando ROUND_HALF_UP."""
    valor = monto if isinstance(monto, Decimal) else Decimal(str(monto))
    return float(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def crear_calculador_multa(tarifa_minuto_soles: float) -> Callable[[int], float]:
    """Función currificada que fija la tarifa y calcula la multa por exceso."""
    tarifa = Decimal(str(tarifa_minuto_soles))

    def calcular_por_exceso(minutos_exceso: int) -> float:
        exceso_valido = max(0, minutos_exceso)
        return redondear_soles(Decimal(exceso_valido) * tarifa)

    return calcular_por_exceso


def calcular_multa_entrega(
    entrega: Entrega,
    estado_arribo: str,
    minutos_exceso: int,
) -> float:
    """Calcula la multa en soles según el estado de arribo y minutos de exceso."""
    if estado_arribo == ESTADO_PENDIENTE:
        return 0.0

    if estado_arribo not in ESTADOS_ARRIBO:
        raise ValueError(f"Estado de arribo no reconocido: '{estado_arribo}'.")

    if estado_arribo in ESTADOS_CUMPLIMIENTO_SLA:
        return 0.0

    if estado_arribo == "no_presentado":
        return redondear_soles(entrega.proveedor.penalidad_inasistencia_soles)

    calculador = crear_calculador_multa(entrega.proveedor.tarifa_minuto_soles)
    return calculador(minutos_exceso)


def evaluar_entrega(entrega: Entrega) -> EvaluacionEntrega:
    """Evalúa una entrega aplicando las reglas SLA y calculando su multa."""
    minutos_retraso = calcular_minutos_retraso(
        entrega.hora_cita,
        entrega.hora_llegada,
        entrega.no_presentado,
    )
    estado_arribo = clasificar_estado_arribo(
        entrega.hora_cita,
        entrega.hora_llegada,
        entrega.proveedor.tolerancia_minutos,
        entrega.no_presentado,
    )
    minutos_exceso = (
        0
        if estado_arribo in ("no_presentado", ESTADO_PENDIENTE)
        else calcular_minutos_exceso(
            minutos_retraso, entrega.proveedor.tolerancia_minutos
        )
    )
    accion_operativa = determinar_accion_operativa(estado_arribo, entrega.criticidad)
    multa_soles = calcular_multa_entrega(entrega, estado_arribo, minutos_exceso)
    es_incidencia = es_incidencia_sla(estado_arribo)
    explicacion_regla = explicar_regla_operativa(
        estado_arribo,
        entrega.criticidad,
        accion_operativa,
    )

    return EvaluacionEntrega(
        entrega=entrega,
        minutos_retraso=minutos_retraso,
        minutos_exceso=minutos_exceso,
        estado_arribo=estado_arribo,
        accion_operativa=accion_operativa,
        multa_soles=multa_soles,
        es_incidencia=es_incidencia,
        explicacion_regla=explicacion_regla,
    )


def evaluar_entrega_segura(entrega: Entrega) -> Resultado[EvaluacionEntrega]:
    """Evalúa una entrega dentro del Functor Resultado para manejo seguro."""
    return Resultado(valor=entrega).fmap(evaluar_entrega)


def liquidar_entregas(entregas: Iterable[Entrega]) -> tuple[EvaluacionEntrega, ...]:
    """Evalúa y liquida una colección de entregas mediante transformación funcional."""
    return tuple(map(evaluar_entrega, entregas))


def _monto_multa(evaluacion: EvaluacionEntrega) -> float:
    """Extrae el monto de la multa en soles de una evaluación."""
    return evaluacion.multa_soles


obtener_multa_de_entrega: Callable[[Entrega], float] = componer(
    _monto_multa,
    evaluar_entrega,
)


def extraer_multas_soles(evaluaciones: Iterable[EvaluacionEntrega]) -> tuple[float, ...]:
    """Proyecta únicamente los montos de multa en soles de cada evaluación."""
    return tuple(map(_monto_multa, evaluaciones))
