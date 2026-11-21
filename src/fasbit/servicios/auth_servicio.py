"""Servicios puros de autenticación, hash de contraseñas y control de roles."""

from collections.abc import Iterable

from werkzeug.security import check_password_hash, generate_password_hash

from fasbit.modelos.usuario_modelo import Usuario


def generar_hash_contrasena(contrasena: str) -> str:
    """Genera un hash seguro usando pbkdf2:sha256 con Werkzeug."""
    if not contrasena:
        raise ValueError("La contraseña no puede estar vacía.")
    return generate_password_hash(contrasena, method="pbkdf2:sha256")


def verificar_contrasena(password_hash: str, contrasena: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con su hash."""
    if not password_hash or not contrasena:
        return False
    return check_password_hash(password_hash, contrasena)


def autenticar_usuario(
    usuarios: Iterable[Usuario],
    nombre_usuario: str,
    contrasena: str,
) -> Usuario | None:
    """Valida credenciales y estado activo de un usuario en la colección."""
    usuario_norm = nombre_usuario.strip().lower()
    if not usuario_norm or not contrasena:
        return None

    candidato = next(
        filter(
            lambda item: item.activo and item.usuario.strip().lower() == usuario_norm,
            usuarios,
        ),
        None,
    )
    if candidato is None:
        return None

    return (
        candidato if verificar_contrasena(candidato.password_hash, contrasena) else None
    )


def tiene_rol(usuario: Usuario | None, roles_permitidos: tuple[str, ...]) -> bool:
    """Comprueba si el usuario está activo y posee alguno de los roles permitidos."""
    return usuario is not None and usuario.activo and usuario.rol in roles_permitidos
