"""Re-exportación de los Blueprints de Flask del sistema."""

from fasbit.controladores.auth_controlador import auth_bp
from fasbit.controladores.recepcion_controlador import recepcion_bp
from fasbit.controladores.usuario_controlador import usuario_bp

__all__ = ["auth_bp", "recepcion_bp", "usuario_bp"]
