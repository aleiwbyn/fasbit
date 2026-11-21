"""Controlador de administración de usuarios exclusivo para rol admin."""

from typing import Any

from flask import Blueprint, current_app, g, redirect, render_template, request, url_for

from fasbit.controladores.auth_controlador import requiere_rol, requiere_sesion
from fasbit.repositorios.usuario_repositorio import cargar_usuarios, guardar_usuarios
from fasbit.servicios.usuario_servicio import (
    alternar_estado_usuario,
    cambiar_rol_usuario,
    crear_usuario,
)

usuario_bp = Blueprint("usuarios", __name__)


def _respuesta_usuarios(
    usuarios: tuple[Any, ...],
    mensaje: str | None = None,
    error: str | None = None,
    codigo_no_htmx: int = 200,
) -> Any:
    """Responde con parcial HTMX o vista completa según el tipo de petición."""
    if request.headers.get("HX-Request") == "true":
        return render_template(
            "parciales/_tabla_usuarios.html",
            usuarios=usuarios,
            mensaje=mensaje,
            error=error,
        )
    if error:
        return (
            render_template(
                "usuarios.html",
                usuarios=usuarios,
                mensaje=mensaje,
                error=error,
            ),
            codigo_no_htmx,
        )
    return redirect(url_for("usuarios.listar_usuarios"))


@usuario_bp.get("/usuarios")
@requiere_sesion
@requiere_rol("admin")
def listar_usuarios() -> str:
    """Muestra el panel de gestión de cuentas de acceso."""
    usuarios = cargar_usuarios(current_app.config["RUTA_USUARIOS"])
    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        mensaje=None,
        error=None,
    )


@usuario_bp.post("/usuarios/crear")
@requiere_sesion
@requiere_rol("admin")
def crear() -> Any:
    """Crea una nueva cuenta de usuario con contraseña encriptada."""
    ruta_usuarios = current_app.config["RUTA_USUARIOS"]
    usuarios = cargar_usuarios(ruta_usuarios)
    try:
        nuevo, actualizados = crear_usuario(
            usuarios_existentes=usuarios,
            nombre_usuario=request.form.get("usuario", ""),
            nombre_completo=request.form.get("nombre_completo", ""),
            rol=request.form.get("rol", "operador"),
            contrasena=request.form.get("contrasena", ""),
        )
        guardar_usuarios(ruta_usuarios, actualizados)
    except ValueError as exc:
        return _respuesta_usuarios(usuarios, error=str(exc), codigo_no_htmx=400)

    return _respuesta_usuarios(
        actualizados,
        mensaje=f"Usuario '{nuevo.usuario}' creado correctamente.",
    )


@usuario_bp.post("/usuarios/<id_usuario>/rol")
@requiere_sesion
@requiere_rol("admin")
def actualizar_rol(id_usuario: str) -> Any:
    """Cambia el rol asignado a una cuenta existente."""
    ruta_usuarios = current_app.config["RUTA_USUARIOS"]
    usuarios = cargar_usuarios(ruta_usuarios)
    try:
        actualizados = cambiar_rol_usuario(
            usuarios=usuarios,
            id_usuario=id_usuario,
            nuevo_rol=request.form.get("rol", ""),
            id_admin_actual=g.usuario_actual.id_usuario,
        )
        guardar_usuarios(ruta_usuarios, actualizados)
    except ValueError as exc:
        return _respuesta_usuarios(usuarios, error=str(exc), codigo_no_htmx=400)

    return _respuesta_usuarios(actualizados, mensaje="Rol actualizado correctamente.")


@usuario_bp.post("/usuarios/<id_usuario>/estado")
@requiere_sesion
@requiere_rol("admin")
def actualizar_estado(id_usuario: str) -> Any:
    """Activa o desactiva una cuenta de usuario existente."""
    ruta_usuarios = current_app.config["RUTA_USUARIOS"]
    usuarios = cargar_usuarios(ruta_usuarios)
    try:
        actualizados = alternar_estado_usuario(
            usuarios=usuarios,
            id_usuario=id_usuario,
            id_admin_actual=g.usuario_actual.id_usuario,
        )
        guardar_usuarios(ruta_usuarios, actualizados)
    except ValueError as exc:
        return _respuesta_usuarios(usuarios, error=str(exc), codigo_no_htmx=400)

    return _respuesta_usuarios(actualizados, mensaje="Estado de cuenta actualizado.")
