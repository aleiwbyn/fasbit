"""Fábrica de la aplicación Flask y configuración global del sistema fasbit."""

import os
from pathlib import Path
from typing import Any

from flask import Flask, g, render_template_string, session

from fasbit.controladores import auth_bp, recepcion_bp, usuario_bp
from fasbit.modelos import (
    ACCIONES_OPERATIVAS,
    CRITICIDADES_VALIDAS,
    ESTADOS_ARRIBO,
    ROLES_VALIDOS,
)
from fasbit.repositorios.usuario_repositorio import cargar_usuarios
from fasbit.servicios.usuario_servicio import buscar_usuario_por_id

ETIQUETAS_ESTADO: dict[str, str] = {
    "a_tiempo": "A tiempo",
    "dentro_de_tolerancia": "En tolerancia",
    "retraso_leve": "Retraso leve",
    "retraso_grave": "Retraso grave",
    "no_presentado": "No vino",
    "pendiente": "Pendiente",
}

ETIQUETAS_ACCION: dict[str, str] = {
    "admision_prioritaria": "Recibir primero",
    "admision_estandar": "Recibir normal",
    "reprogramacion_urgente": "Reprogramar urgente",
    "recepcion_fin_turno": "Al final del día",
    "rechazo_o_cancelacion": "Cancelar entrega",
    "pendiente": "En espera",
}

ETIQUETAS_CRITICIDAD: dict[str, str] = {
    "alta": "Alta",
    "media": "Media",
    "baja": "Baja",
}

ETIQUETAS_ROL: dict[str, str] = {
    "admin": "Administrador",
    "operador": "Operador",
}

_PLANTILLA_ERROR = """{% extends "base.html" %}
{% block titulo %}{{ titulo }} — fasbit{% endblock %}
{% block contenido %}
<section class="panel-sistema estado-sistema">
  <h1>{{ titulo }}</h1>
  <p>{{ mensaje }}</p>
  <a href="{{ url_for('recepcion.panel') if usuario_actual else url_for('auth.login') }}" role="button" class="btn-primario">
    Volver al inicio
  </a>
</section>
{% endblock %}
"""


def _formatear_soles(monto: float) -> str:
    """Formatea un monto numérico en soles peruanos."""
    return f"S/ {monto:,.2f}"


def crear_app(config: dict[str, Any] | None = None) -> Flask:
    """Crea y configura una instancia lista de la aplicación Flask."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    raiz_proyecto = Path(__file__).resolve().parents[2]
    ruta_datos = raiz_proyecto / "data"

    app.config.update(
        SECRET_KEY=os.environ.get(
            "FASBIT_SECRET_KEY", "fasbit-clave-desarrollo-2026"
        ),
        RUTA_ENTREGAS=ruta_datos / "entregas.json",
        RUTA_USUARIOS=ruta_datos / "usuarios.json",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if config:
        app.config.update(config)

    app.config["RUTA_ENTREGAS"] = Path(app.config["RUTA_ENTREGAS"])
    app.config["RUTA_USUARIOS"] = Path(app.config["RUTA_USUARIOS"])

    app.jinja_env.filters["soles"] = _formatear_soles

    @app.before_request
    def cargar_usuario_en_sesion() -> None:
        id_usuario = session.get("id_usuario")
        if not id_usuario:
            g.usuario_actual = None
            return

        usuarios = cargar_usuarios(app.config["RUTA_USUARIOS"])
        usuario = buscar_usuario_por_id(usuarios, str(id_usuario))
        if usuario is None or not usuario.activo:
            session.clear()
            g.usuario_actual = None
            return

        g.usuario_actual = usuario

    @app.context_processor
    def inyectar_contexto_global() -> dict[str, Any]:
        return {
            "usuario_actual": g.get("usuario_actual"),
            "ETIQUETAS_ESTADO": ETIQUETAS_ESTADO,
            "ETIQUETAS_ACCION": ETIQUETAS_ACCION,
            "ETIQUETAS_CRITICIDAD": ETIQUETAS_CRITICIDAD,
            "ETIQUETAS_ROL": ETIQUETAS_ROL,
            "ESTADOS_ARRIBO": ESTADOS_ARRIBO,
            "ACCIONES_OPERATIVAS": ACCIONES_OPERATIVAS,
            "CRITICIDADES_VALIDAS": CRITICIDADES_VALIDAS,
            "ROLES_VALIDOS": ROLES_VALIDOS,
        }

    @app.errorhandler(403)
    def acceso_denegado(_error: Any) -> tuple[str, int]:
        return (
            render_template_string(
                _PLANTILLA_ERROR,
                titulo="Acceso restringido",
                mensaje="No tienes permiso para ver esta página.",
            ),
            403,
        )

    @app.errorhandler(404)
    def no_encontrado(_error: Any) -> tuple[str, int]:
        return (
            render_template_string(
                _PLANTILLA_ERROR,
                titulo="Página no encontrada",
                mensaje="No encontramos la página que buscas.",
            ),
            404,
        )

    app.register_blueprint(auth_bp)
    app.register_blueprint(recepcion_bp)
    app.register_blueprint(usuario_bp)

    return app
