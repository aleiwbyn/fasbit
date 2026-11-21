"""Modelo inmutable para cuentas de usuario y roles del sistema."""

from dataclasses import dataclass

ROLES_VALIDOS: tuple[str, ...] = ("admin", "operador")


@dataclass(frozen=True)
class Usuario:
    """Cuenta de usuario autenticada con hash de contraseña y estado."""

    id_usuario: str
    usuario: str
    nombre_completo: str
    rol: str
    password_hash: str
    activo: bool = True
