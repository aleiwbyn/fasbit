"""Re-exportación de funciones de persistencia JSON."""

from fasbit.repositorios.entrega_repositorio import cargar_entregas, guardar_entregas
from fasbit.repositorios.usuario_repositorio import cargar_usuarios, guardar_usuarios

__all__ = [
    "cargar_entregas",
    "cargar_usuarios",
    "guardar_entregas",
    "guardar_usuarios",
]
