"""Gestión funcional de cuentas de usuario y reglas de seguridad de roles."""

from collections.abc import Iterable
from dataclasses import replace

from fasbit.modelos.usuario_modelo import ROLES_VALIDOS, Usuario
from fasbit.servicios.auth_servicio import generar_hash_contrasena

LONGITUD_MINIMA_CONTRASENA: int = 6


def buscar_usuario_por_id(
    usuarios: Iterable[Usuario],
    id_usuario: str,
) -> Usuario | None:
    """Encuentra un usuario por su identificador usando filter()."""
    return next(
        filter(lambda item: item.id_usuario == id_usuario, usuarios),
        None,
    )


def _siguiente_id_usuario(usuarios_existentes: Iterable[Usuario]) -> str:
    """Genera el siguiente identificador correlativo con formato USR-XX."""
    numeros = []
    for item in usuarios_existentes:
        if item.id_usuario.startswith("USR-"):
            sufijo = item.id_usuario[4:]
            if sufijo.isdigit():
                numeros.append(int(sufijo))
    siguiente = max(numeros, default=0) + 1
    return f"USR-{siguiente:02d}"


def _contar_admins_activos(usuarios: Iterable[Usuario]) -> int:
    """Cuenta cuántos usuarios administradores activos existen."""
    return len(tuple(filter(lambda item: item.activo and item.rol == "admin", usuarios)))


def crear_usuario(
    usuarios_existentes: Iterable[Usuario],
    nombre_usuario: str,
    nombre_completo: str,
    rol: str,
    contrasena: str,
) -> tuple[Usuario, tuple[Usuario, ...]]:
    """Valida reglas de cuenta y retorna el nuevo Usuario junto con la lista."""
    tupla_actual = tuple(usuarios_existentes)
    usuario_limpio = nombre_usuario.strip().lower()
    nombre_limpio = nombre_completo.strip()
    rol_limpio = rol.strip().lower()

    if not usuario_limpio or any(ch.isspace() for ch in usuario_limpio):
        raise ValueError("El nombre de usuario es obligatorio y no debe tener espacios.")
    if any(u.usuario.strip().lower() == usuario_limpio for u in tupla_actual):
        raise ValueError(f"Ya existe una cuenta con el usuario '{usuario_limpio}'.")
    if not nombre_limpio:
        raise ValueError("El nombre completo es obligatorio.")
    if rol_limpio not in ROLES_VALIDOS:
        raise ValueError("Rol inválido. Seleccione 'admin' o 'operador'.")
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        raise ValueError(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres."
        )

    nuevo_usuario = Usuario(
        id_usuario=_siguiente_id_usuario(tupla_actual),
        usuario=usuario_limpio,
        nombre_completo=nombre_limpio,
        rol=rol_limpio,
        password_hash=generar_hash_contrasena(contrasena),
        activo=True,
    )
    return nuevo_usuario, tupla_actual + (nuevo_usuario,)


def cambiar_rol_usuario(
    usuarios: Iterable[Usuario],
    id_usuario: str,
    nuevo_rol: str,
    id_admin_actual: str,
) -> tuple[Usuario, ...]:
    """Actualiza el rol de una cuenta protegiendo al administrador en sesión."""
    tupla_actual = tuple(usuarios)
    rol_limpio = nuevo_rol.strip().lower()
    if rol_limpio not in ROLES_VALIDOS:
        raise ValueError("Rol inválido. Seleccione 'admin' o 'operador'.")

    objetivo = buscar_usuario_por_id(tupla_actual, id_usuario)
    if objetivo is None:
        raise ValueError("No se encontró el usuario solicitado.")
    if objetivo.id_usuario == id_admin_actual and rol_limpio != "admin":
        raise ValueError("No puede cambiar su propio rol de administrador en sesión.")

    if (
        objetivo.rol == "admin"
        and objetivo.activo
        and rol_limpio != "admin"
        and _contar_admins_activos(tupla_actual) <= 1
    ):
        raise ValueError("Debe permanecer al menos un administrador activo.")

    def _aplicar_rol(item: Usuario) -> Usuario:
        return replace(item, rol=rol_limpio) if item.id_usuario == id_usuario else item

    return tuple(map(_aplicar_rol, tupla_actual))


def alternar_estado_usuario(
    usuarios: Iterable[Usuario],
    id_usuario: str,
    id_admin_actual: str,
) -> tuple[Usuario, ...]:
    """Activa o desactiva una cuenta impidiendo bloquear al propio administrador."""
    tupla_actual = tuple(usuarios)
    objetivo = buscar_usuario_por_id(tupla_actual, id_usuario)
    if objetivo is None:
        raise ValueError("No se encontró el usuario solicitado.")
    if objetivo.id_usuario == id_admin_actual and objetivo.activo:
        raise ValueError("No puede desactivar su propia cuenta mientras está en sesión.")

    if (
        objetivo.activo
        and objetivo.rol == "admin"
        and _contar_admins_activos(tupla_actual) <= 1
    ):
        raise ValueError("No se puede desactivar al último administrador activo.")

    def _alternar_activo(item: Usuario) -> Usuario:
        return (
            replace(item, activo=not item.activo)
            if item.id_usuario == id_usuario
            else item
        )

    return tuple(map(_alternar_activo, tupla_actual))
