"""
Rutas REST de FASBIT (/api/v1/...).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException

from fasbit.domain.exceptions import (
    InvalidRouteQueryError,
    PrologEngineError,
    ScenarioNotFoundError,
)
from fasbit.interfaces.api.schemas import (
    RouteQueryRequest,
    serialize_route,
    serialize_simulation_result,
)
from fasbit.services.planner_service import PlannerService
from fasbit.services.simulation_service import SimulationService

router = APIRouter(prefix="/api/v1", tags=["FASBIT Planner"])


@router.get("/health")
def get_health() -> dict[str, Any]:
    try:
        planner = PlannerService()
        prolog_health = planner.bridge.health_check()
        return {
            "status": "ok",
            "prolog": prolog_health,
            "swipl_executable": planner.bridge.swipl_executable,
        }
    except PrologEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/snapshot")
def get_snapshot() -> dict[str, Any]:
    try:
        planner = PlannerService()
        return planner.get_system_snapshot()
    except PrologEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/routes/optimize")
def optimize_routes(req: RouteQueryRequest) -> dict[str, Any]:
    try:
        planner = PlannerService()
        routes = planner.find_optimal_routes(
            origen=req.origen,
            destino=req.destino,
            hora_salida_min=req.hora_salida_min,
            ventana_inicio_min=req.ventana_inicio_min,
            plazo_maximo_min=req.plazo_maximo_min,
            multa_por_minuto=req.multa_por_minuto,
            traffic_overrides=[t.model_dump() for t in req.traffic_overrides],
        )
        serialized = [serialize_route(r) for r in routes]
        return {
            "total_alternativas": len(serialized),
            "ruta_optima": serialized[0] if serialized else None,
            "alternativas": serialized,
        }
    except InvalidRouteQueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PrologEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/scenarios")
def list_scenarios() -> dict[str, Any]:
    sim = SimulationService()
    return {
        "scenarios": [asdict(s) for s in sim.list_scenarios()],
    }


@router.get("/simulate/{scenario_id}")
def run_scenario_simulation(scenario_id: str) -> dict[str, Any]:
    try:
        sim = SimulationService()
        result = sim.run_scenario(scenario_id)
        return serialize_simulation_result(result)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PrologEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/simulate")
def run_all_simulations() -> dict[str, Any]:
    try:
        sim = SimulationService()
        results = sim.run_all_scenarios()
        return {
            "resultados": [serialize_simulation_result(r) for r in results],
        }
    except PrologEngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

