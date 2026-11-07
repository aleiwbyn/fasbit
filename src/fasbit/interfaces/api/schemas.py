"""
Esquemas Pydantic y serializadores puros para la API REST.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from pydantic import BaseModel, Field

from fasbit.domain.models import (
    RouteEvaluation,
    ScenarioSimulationResult,
    minutes_to_hhmm,
)


class TrafficOverrideInput(BaseModel):
    origen: str
    destino: str
    nivel: str = Field(pattern="^(bajo|moderado|alto|critico)$")


class RouteQueryRequest(BaseModel):
    origen: str = "puerto_callao"
    destino: str = "almacen_central"
    hora_salida_min: float = Field(default=430, ge=0, le=1439)
    ventana_inicio_min: float = Field(default=475, ge=0, le=1439)
    plazo_maximo_min: float = Field(default=500, ge=0, le=1800)
    multa_por_minuto: float = Field(default=4.5, ge=0)
    traffic_overrides: list[TrafficOverrideInput] = Field(default_factory=list)


def serialize_route(route: RouteEvaluation) -> dict[str, Any]:
    """Serializa una evaluación de ruta añadiendo formatos legibles HH:MM."""
    data = asdict(route)
    data["hora_salida_hhmm"] = route.hora_salida_hhmm
    data["hora_llegada_hhmm"] = route.hora_llegada_hhmm
    return data


def serialize_simulation_result(res: ScenarioSimulationResult) -> dict[str, Any]:
    """Serializa el resultado completo de simulación con marcas horarias HH:MM."""
    base_list = []
    for b in res.tareas_base:
        item = asdict(b)
        item["ruta"] = serialize_route(b.ruta)
        item["plazo_maximo_hhmm"] = minutes_to_hhmm(b.plazo_maximo_min)
        item["ventana_recepcion_hhmm"] = (
            f"{minutes_to_hhmm(b.inicio_recepcion_min)} - {minutes_to_hhmm(b.fin_recepcion_min)}"
        )
        base_list.append(item)

    opt_list = []
    for t in res.tareas_optimizadas:
        item = asdict(t)
        item["ruta"] = serialize_route(t.ruta)
        item["plazo_maximo_hhmm"] = minutes_to_hhmm(t.plazo_maximo_min)
        item["ventana_descarga_hhmm"] = (
            f"{minutes_to_hhmm(t.inicio_descarga_min)} - {minutes_to_hhmm(t.fin_descarga_min)}"
        )
        opt_list.append(item)

    return {
        "escenario": asdict(res.escenario),
        "kpis_base": asdict(res.kpis_base),
        "kpis_optimizado": asdict(res.kpis_optimizado),
        "impacto": asdict(res.impacto),
        "tareas_base": base_list,
        "tareas_optimizadas": opt_list,
        "ocupacion_muelles": list(res.ocupacion_muelles),
    }

