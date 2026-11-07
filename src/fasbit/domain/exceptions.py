"""Excepciones de dominio e infraestructura para FASBIT."""


class FasbitError(Exception):
    """Excepción base del sistema FASBIT."""


class PrologEngineError(FasbitError):
    """Error al ejecutar o interpretar el motor lógico SWI-Prolog."""


class ScenarioNotFoundError(FasbitError):
    """El escenario de simulación solicitado no existe."""


class InvalidRouteQueryError(FasbitError):
    """Parámetros inválidos para consulta de optimización de rutas."""

