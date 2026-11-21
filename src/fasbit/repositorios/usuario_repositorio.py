"""Repositorio JSON para lectura y escritura de cuentas de usuario."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from fasbit.modelos.usuario_modelo import Usuario


def _diccionario_a_usuario(datos: dict[str, Any]) -> Usuario:
    """Convierte un diccionario JSON en una instancia inmutable de Usuario."""
    return Usuario(
        id_usuario=str(datos["id_usuario"]),
        usuario=str(datos["usuario"]),
        nombre_completo=str(datos["nombre_completo"]),
        rol=str(datos["rol"]),
        password_hash=str(datos["password_hash"]),
        activo=bool(datos.get("activo", True)),
    )


def _usuario_a_diccionario(usuario: Usuario) -> dict[str, Any]:
    """Serializa una instancia de Usuario a diccionario JSON."""
    return {
        "id_usuario": usuario.id_usuario,
        "usuario": usuario.usuario,
        "nombre_completo": usuario.nombre_completo,
        "rol": usuario.rol,
        "password_hash": usuario.password_hash,
        "activo": usuario.activo,
    }


def cargar_usuarios(ruta_archivo: Path) -> tuple[Usuario, ...]:
    """Lee el archivo JSON de usuarios y devuelve una tupla inmutable."""
    if not ruta_archivo.exists():
        return ()
    contenido = ruta_archivo.read_text(encoding="utf-8").strip()
    if not contenido:
        return ()
    registros: list[dict[str, Any]] = json.loads(contenido)
    return tuple(map(_diccionario_a_usuario, registros))


def guardar_usuarios(ruta_archivo: Path, usuarios: Iterable[Usuario]) -> None:
    """Persiste la colección de usuarios en formato JSON UTF-8 ordenado."""
    ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
    ordenados = sorted(usuarios, key=lambda item: item.id_usuario)
    datos = [_usuario_a_diccionario(item) for item in ordenados]
    ruta_archivo.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
