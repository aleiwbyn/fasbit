"""Modelo inmutable para proveedores logísticos y sus parámetros contractuales."""

from dataclasses import dataclass

CRITICIDADES_VALIDAS: tuple[str, ...] = ("alta", "media", "baja")


@dataclass(frozen=True)
class Proveedor:
    """Representa un proveedor con sus condiciones SLA y tarifas de penalidad."""

    id_proveedor: str
    nombre: str
    ruc: str
    tolerancia_minutos: int
    tarifa_minuto_soles: float
    penalidad_inasistencia_soles: float
