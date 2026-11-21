"""Re-exportación de los modelos inmutables y constantes del dominio."""

from fasbit.modelos.entrega_modelo import (
    ACCIONES_OPERATIVAS,
    ESTADOS_ARRIBO,
    ESTADOS_CUMPLIMIENTO_SLA,
    ESTADOS_INCIDENCIA,
    Entrega,
    EvaluacionEntrega,
)
from fasbit.modelos.proveedor_modelo import CRITICIDADES_VALIDAS, Proveedor
from fasbit.modelos.usuario_modelo import ROLES_VALIDOS, Usuario

__all__ = [
    "ACCIONES_OPERATIVAS",
    "CRITICIDADES_VALIDAS",
    "ESTADOS_ARRIBO",
    "ESTADOS_CUMPLIMIENTO_SLA",
    "ESTADOS_INCIDENCIA",
    "ROLES_VALIDOS",
    "Entrega",
    "EvaluacionEntrega",
    "Proveedor",
    "Usuario",
]
