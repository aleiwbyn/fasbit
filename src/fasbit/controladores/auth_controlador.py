"""Controlador de autenticación, sesiones y decoradores de acceso por rol."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from fasbit.repositorios.usuario_repositorio import cargar_usuarios
from fasbit.servicios.auth_servicio import autenticar_usuario, tiene_rol

auth_bp = Blueprint("auth", __name__)


def requiere_sesion(funcion: Callable[..., Any]) -> Callable[..., Any]:
    """Protege rutas exigiendo un usuario activo en sesión."""

    @wraps(funcion)
    def envoltura(*args: Any, **kwargs: Any) -> Any:
        if g.get("usuario_actual") is None:
            if request.headers.get("HX-Request") == "true":
                return ("", 401, {"HX-Redirect": url_for("auth.login")})
            return redirect(url_for("auth.login"))
        return funcion(*args, **kwargs)

    return envoltura


def requiere_rol(*roles_permitidos: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Restringe una vista únicamente a los roles especificados."""

    def decorador(funcion: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(funcion)
        def envoltura(*args: Any, **kwargs: Any) -> Any:
            if not tiene_rol(g.get("usuario_actual"), roles_permitidos):
                abort(403)
            return funcion(*args, **kwargs)

        return envoltura

    return decorador


@auth_bp.get("/")
def inicio() -> Any:
    """Redirige al panel operativo si hay sesión o al login en caso contrario."""
    if g.get("usuario_actual") is not None:
        return redirect(url_for("recepcion.panel"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Muestra el formulario de acceso y valida credenciales."""
    if request.method == "GET":
        if g.get("usuario_actual") is not None:
            return redirect(url_for("recepcion.panel"))
        return render_template("login.html", error=None, usuario_ingresado="")

    nombre_usuario = request.form.get("usuario", "")
    contrasena = request.form.get("contrasena", "")
    usuarios = cargar_usuarios(current_app.config["RUTA_USUARIOS"])
    usuario_valido = autenticar_usuario(usuarios, nombre_usuario, contrasena)

    if usuario_valido is None:
        return (
            render_template(
                "login.html",
                error="Usuario o contraseña incorrectos, o la cuenta está desactivada.",
                usuario_ingresado=nombre_usuario.strip(),
            ),
            401,
        )

    session.clear()
    session["id_usuario"] = usuario_valido.id_usuario
    return redirect(url_for("recepcion.panel"))


@auth_bp.post("/logout")
def logout() -> Any:
    """Cierra la sesión activa y redirige a la pantalla de login."""
    session.clear()
    return redirect(url_for("auth.login"))
