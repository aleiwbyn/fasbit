"""
Pruebas de endpoints REST y Dashboard Web mediante FastAPI TestClient.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from fasbit.interfaces.api.app import app

client = TestClient(app)


def test_health_and_dashboard_root() -> None:
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_root = client.get("/")
    assert r_root.status_code == 200
    html = r_root.text
    assert "FASBIT" in html
    assert 'role="tablist"' in html
    assert 'id="panel-dispatch"' in html
    assert 'id="panel-warehouse"' in html
    assert 'id="panel-prolog"' in html
    assert 'id="dockGantt"' in html
    assert 'id="orderInspector"' in html


def test_static_design_system_assets() -> None:
    r_css = client.get("/static/styles.css")
    assert r_css.status_code == 200
    assert "--paper-canvas" in r_css.text
    assert "tabular-nums" in r_css.text
    assert "prefers-reduced-motion" in r_css.text

    r_js = client.get("/static/app.js")
    assert r_js.status_code == 200
    assert "renderOrderInspector" in r_js.text
    assert "renderDockGantt" in r_js.text
    assert "executePrologLabQuery" in r_js.text


def test_simulate_endpoint_and_route_optimizer() -> None:
    r_sim = client.get("/api/v1/simulate/hora_punta_estandar")
    assert r_sim.status_code == 200
    payload = r_sim.json()
    assert payload["kpis_optimizado"]["tasa_puntualidad_pct"] == 100.0
    assert payload["impacto"]["ahorro_total_soles"] > 0

    r_opt = client.post(
        "/api/v1/routes/optimize",
        json={
            "origen": "parque_ind_ate",
            "destino": "almacen_central",
            "hora_salida_min": 450,
            "ventana_inicio_min": 465,
            "plazo_maximo_min": 480,
            "multa_por_minuto": 3.2,
        },
    )
    assert r_opt.status_code == 200
    opt_data = r_opt.json()
    assert opt_data["total_alternativas"] >= 2
    assert opt_data["ruta_optima"]["estado_puntualidad"] == "a_tiempo"

