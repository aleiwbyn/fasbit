"""Pruebas de integración para autenticación, roles, controladores y HTMX."""

import shutil
from pathlib import Path

import pytest

from fasbit.app import crear_app
from fasbit.repositorios import cargar_entregas, cargar_usuarios
from fasbit.servicios.auth_servicio import (
    autenticar_usuario,
    generar_hash_contrasena,
    verificar_contrasena,
)


@pytest.fixture()
def cliente_temporal(tmp_path: Path):
    raiz = Path(__file__).resolve().parents[1]
    ruta_entregas = tmp_path / "entregas.json"
    ruta_usuarios = tmp_path / "usuarios.json"
    shutil.copy2(raiz / "data" / "entregas.json", ruta_entregas)
    shutil.copy2(raiz / "data" / "usuarios.json", ruta_usuarios)

    app = crear_app(
        {
            "TESTING": True,
            "SECRET_KEY": "clave-pruebas",
            "RUTA_ENTREGAS": ruta_entregas,
            "RUTA_USUARIOS": ruta_usuarios,
        }
    )
    with app.test_client() as cliente:
        yield cliente, ruta_entregas, ruta_usuarios


def _iniciar_sesion(cliente, usuario: str, contrasena: str):
    return cliente.post(
        "/login",
        data={"usuario": usuario, "contrasena": contrasena},
        follow_redirects=False,
    )


def test_hash_y_autenticacion_de_servicio(tmp_path: Path) -> None:
    hash_clave = generar_hash_contrasena("secreto123")
    assert hash_clave != "secreto123"
    assert verificar_contrasena(hash_clave, "secreto123") is True
    assert verificar_contrasena(hash_clave, "incorrecto") is False

    raiz = Path(__file__).resolve().parents[1]
    usuarios = cargar_usuarios(raiz / "data" / "usuarios.json")
    assert autenticar_usuario(usuarios, "ADMIN", "admin123") is not None
    assert autenticar_usuario(usuarios, "operador2", "lucia123") is None
    assert autenticar_usuario(usuarios, "admin", "mala") is None


def test_proteccion_sin_sesion_y_login_invalido(cliente_temporal) -> None:
    cliente, _, _ = cliente_temporal

    resp = cliente.get("/recepcion")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    resp_htmx = cliente.get("/recepcion/tabla", headers={"HX-Request": "true"})
    assert resp_htmx.status_code == 401
    assert resp_htmx.headers["HX-Redirect"].endswith("/login")

    resp_login_malo = cliente.post(
        "/login",
        data={"usuario": "admin", "contrasena": "equivocada"},
    )
    assert resp_login_malo.status_code == 401


def test_control_roles_operador_vs_admin(cliente_temporal) -> None:
    cliente, _, ruta_usuarios = cliente_temporal

    login_op = _iniciar_sesion(cliente, "operador", "operador123")
    assert login_op.status_code == 302

    assert cliente.get("/recepcion").status_code == 200
    assert cliente.get("/recepcion/tabla?estado=retraso_grave").status_code == 200
    assert cliente.get("/recepcion/kpis").status_code == 200

    assert cliente.get("/usuarios").status_code == 403
    assert (
        cliente.post(
            "/usuarios/crear",
            data={
                "usuario": "nuevoop",
                "nombre_completo": "Nuevo Operador",
                "rol": "operador",
                "contrasena": "clave123",
            },
        ).status_code
        == 403
    )

    assert cliente.post("/logout").status_code == 302
    assert cliente.get("/recepcion").status_code == 302

    login_admin = _iniciar_sesion(cliente, "admin", "admin123")
    assert login_admin.status_code == 302
    assert cliente.get("/usuarios").status_code == 200

    resp_crear = cliente.post(
        "/usuarios/crear",
        data={
            "usuario": "operador3",
            "nombre_completo": "Marco Diaz",
            "rol": "operador",
            "contrasena": "clave123",
        },
        headers={"HX-Request": "true"},
    )
    assert resp_crear.status_code == 200
    assert "operador3" in resp_crear.get_data(as_text=True)

    resp_rol = cliente.post(
        "/usuarios/USR-02/rol",
        data={"rol": "admin"},
        headers={"HX-Request": "true"},
    )
    assert resp_rol.status_code == 200

    resp_estado = cliente.post(
        "/usuarios/USR-02/estado",
        headers={"HX-Request": "true"},
    )
    assert resp_estado.status_code == 200

    resp_autodesactivar = cliente.post(
        "/usuarios/USR-01/estado",
        headers={"HX-Request": "true"},
    )
    assert resp_autodesactivar.status_code == 200
    assert "No puede desactivar su propia cuenta" in resp_autodesactivar.get_data(
        as_text=True
    )

    usuarios_guardados = cargar_usuarios(ruta_usuarios)
    assert any(u.usuario == "operador3" for u in usuarios_guardados)


def test_flujo_htmx_evaluar_simular_y_guardar(cliente_temporal) -> None:
    cliente, ruta_entregas, _ = cliente_temporal
    _iniciar_sesion(cliente, "operador", "operador123")

    entregas_antes = cargar_entregas(ruta_entregas)
    assert entregas_antes[0].hora_llegada == "07:20"

    resp_simular = cliente.post(
        "/recepcion/evaluar",
        data={
            "tipo_operacion": "existente",
            "id_entrega": "ENT-001",
            "hora_llegada": "08:20",
            "modo": "simular",
        },
        headers={"HX-Request": "true"},
    )
    html_sim = resp_simular.get_data(as_text=True)
    assert resp_simular.status_code == 200
    assert "Solo prueba (no se guardó)" in html_sim
    assert "hx-swap-oob" not in html_sim
    assert cargar_entregas(ruta_entregas)[0].hora_llegada == "07:20"

    resp_guardar = cliente.post(
        "/recepcion/evaluar",
        data={
            "tipo_operacion": "existente",
            "id_entrega": "ENT-001",
            "hora_llegada": "08:20",
            "observacion": "Demora confirmada en puerta",
            "modo": "guardar",
        },
        headers={"HX-Request": "true"},
    )
    html_guardado = resp_guardar.get_data(as_text=True)
    assert resp_guardar.status_code == 200
    assert "Guardado correctamente" in html_guardado
    assert 'id="bloque-kpis" hx-swap-oob="true"' in html_guardado
    assert 'id="contenedor-tabla-entregas" hx-swap-oob="true"' in html_guardado
    assert cargar_entregas(ruta_entregas)[0].hora_llegada == "08:20"

    resp_nueva = cliente.post(
        "/recepcion/evaluar",
        data={
            "tipo_operacion": "nueva",
            "id_proveedor": "PROV-01",
            "codigo_orden": "OC-2026-0199",
            "hora_cita": "12:00",
            "criticidad": "alta",
            "hora_llegada": "12:10",
            "modo": "guardar",
        },
        headers={"HX-Request": "true"},
    )
    assert resp_nueva.status_code == 200
    assert len(cargar_entregas(ruta_entregas)) == 11

    resp_error = cliente.post(
        "/recepcion/evaluar",
        data={
            "tipo_operacion": "existente",
            "id_entrega": "ENT-001",
            "hora_llegada": "",
            "modo": "guardar",
        },
        headers={"HX-Request": "true"},
    )
    assert resp_error.status_code == 200
    assert "Revisa los datos:" in resp_error.get_data(as_text=True)


def test_eliminacion_admin_y_ventanas_reprogramacion(cliente_temporal) -> None:
    cliente, ruta_entregas, _ = cliente_temporal
    _iniciar_sesion(cliente, "operador", "operador123")

    resp_panel = cliente.get("/recepcion")
    assert resp_panel.status_code == 200
    assert "Avisos de hoy" in resp_panel.get_data(as_text=True)

    # Operador no puede eliminar entregas
    assert cliente.post("/recepcion/entregas/ENT-010/eliminar").status_code == 403

    # Admin sí puede eliminar entregas y dispara actualización OOB de KPIs
    cliente.post("/logout")
    _iniciar_sesion(cliente, "admin", "admin123")

    resp_eval = cliente.post(
        "/recepcion/evaluar",
        data={
            "tipo_operacion": "existente",
            "id_entrega": "ENT-007",
            "hora_llegada": "10:55",
            "modo": "simular",
        },
        headers={"HX-Request": "true"},
    )
    html_eval = resp_eval.get_data(as_text=True)
    assert "Próximos horarios libres" in html_eval
    assert "11:10" in html_eval

    resp_eliminar = cliente.post(
        "/recepcion/entregas/ENT-010/eliminar",
        headers={"HX-Request": "true"},
    )
    assert resp_eliminar.status_code == 200
    html_elim = resp_eliminar.get_data(as_text=True)
    assert 'id="bloque-kpis" hx-swap-oob="true"' in html_elim
    assert len(cargar_entregas(ruta_entregas)) == 9


def test_ui_sin_rastros_tecnologicos(cliente_temporal) -> None:
    from html.parser import HTMLParser

    class _ExtractorTexto(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.partes: list[str] = []

        def handle_data(self, data: str) -> None:
            self.partes.append(data)

    cliente, _, _ = cliente_temporal
    rastros = (
        "declarativ",
        "perezos",
        "∀",
        "∃",
        "htmx",
        "flask",
        "python",
        "picocss",
        "json",
        "functor",
        "criticidad",
        "arribo",
        "ventana",
        "liquidación",
        "penalidad",
        "incidencia",
        "admisión",
        "muelle",
        "resolución",
        "resoluciones",
        "sla",
        "no presentado",
        "contractual",
        "credenciales",
        "distribuidora andina",
        "insumos del pacifico",
        "agroindustrias valle sur",
        "empaques lima norte",
        "farmalogistica",
        "sol naciente",
    )

    html_login = cliente.get("/login").get_data(as_text=True)
    _iniciar_sesion(cliente, "admin", "admin123")
    html_recepcion = cliente.get("/recepcion").get_data(as_text=True)
    html_usuarios = cliente.get("/usuarios").get_data(as_text=True)
    html_eval_sim = cliente.post(
        "/recepcion/evaluar",
        data={
            "tipo_operacion": "existente",
            "id_entrega": "ENT-007",
            "hora_llegada": "10:55",
            "modo": "simular",
        },
        headers={"HX-Request": "true"},
    ).get_data(as_text=True)

    empresas_reales = (
        "Alicorp S.A.A.",
        "Leche Gloria S.A.",
        "San Fernando S.A.",
        "Trupal S.A.",
        "Química Suiza S.A.C.",
        "Molitalia S.A.",
    )
    for empresa in empresas_reales:
        assert empresa in html_recepcion

    for html in (html_login, html_recepcion, html_usuarios, html_eval_sim):
        extractor = _ExtractorTexto()
        extractor.feed(html)
        texto_visible = " ".join(extractor.partes).lower()
        for rastro in rastros:
            assert rastro not in texto_visible, f"Rastro '{rastro}' visible en UI"
