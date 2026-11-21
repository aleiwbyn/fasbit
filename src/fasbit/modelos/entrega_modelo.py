"""Modelos inmutables para entregas programadas y su evaluación SLA."""

from dataclasses import dataclass

from fasbit.modelos.proveedor_modelo import Proveedor

ESTADOS_ARRIBO = (
    "a_tiempo",
    "dentro_de_tolerancia",
    "retraso_leve",
    "retraso_grave",
    "no_presentado",
)

ESTADO_PENDIENTE: str = "pendiente"
ACCION_PENDIENTE: str = "pendiente"

ACCIONES_OPERATIVAS = (
    "admision_prioritaria",
    "admision_estandar",
    "reprogramacion_urgente",
    "recepcion_fin_turno",
    "rechazo_o_cancelacion",
)

ESTADOS_CUMPLIMIENTO_SLA: frozenset[str] = frozenset(
    {"a_tiempo", "dentro_de_tolerancia"}
)

ESTADOS_INCIDENCIA: frozenset[str] = frozenset(
    {"retraso_leve", "retraso_grave", "no_presentado"}
)


@dataclass(frozen=True)
class Entrega:
    """Entrega programada de un proveedor en una ventana horaria del turno."""

    id_entrega: str
    codigo_orden: str
    proveedor: Proveedor
    hora_cita: str
    hora_llegada: str | None
    criticidad: str
    no_presentado: bool = False
    observacion: str = ""


@dataclass(frozen=True)
class EvaluacionEntrega:
    """Resultado inmutable de evaluar las reglas SLA y multa de una entrega."""

    entrega: Entrega
    minutos_retraso: int
    minutos_exceso: int
    estado_arribo: str
    accion_operativa: str
    multa_soles: float
    es_incidencia: bool
    explicacion_regla: str
