"""Reglas puras y declarativas para evaluar llegadas SLA y acciones operativas."""

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from itertools import islice
from types import MappingProxyType

from fasbit.modelos.entrega_modelo import (
    ACCIONES_OPERATIVAS,
    ESTADOS_ARRIBO,
    ESTADOS_INCIDENCIA,
)
from fasbit.modelos.proveedor_modelo import CRITICIDADES_VALIDAS

UMBRAL_RETRASO_LEVE_MINUTOS: int = 30


@dataclass(frozen=True)
class IntervaloMinutos:
    """Intervalo declarativo de minutos para clasificación de ventanas SLA."""

    inicio: int
    fin: int | None
    etiqueta: str


INTERVALO_A_TIEMPO = IntervaloMinutos(0, 0, "a_tiempo")
INTERVALO_RETRASO_LEVE = IntervaloMinutos(
    1, UMBRAL_RETRASO_LEVE_MINUTOS, "retraso_leve"
)
INTERVALO_RETRASO_GRAVE = IntervaloMinutos(
    UMBRAL_RETRASO_LEVE_MINUTOS + 1, None, "retraso_grave"
)


def pertenece_intervalo(valor: int, intervalo: IntervaloMinutos) -> bool:
    """Indica si un valor entero cae dentro de un intervalo SLA (equiv. elem)."""
    return valor >= intervalo.inicio and (
        intervalo.fin is None or valor <= intervalo.fin
    )


def fuera_de_intervalo(valor: int, intervalo: IntervaloMinutos) -> bool:
    """Indica si un valor entero queda fuera del intervalo (equiv. notElem)."""
    return not pertenece_intervalo(valor, intervalo)

REGLAS_ACCION_OPERATIVA: MappingProxyType[tuple[str, str], str] = MappingProxyType(
    {
        ("a_tiempo", "alta"): "admision_prioritaria",
        ("a_tiempo", "media"): "admision_estandar",
        ("a_tiempo", "baja"): "admision_estandar",
        ("dentro_de_tolerancia", "alta"): "admision_prioritaria",
        ("dentro_de_tolerancia", "media"): "admision_estandar",
        ("dentro_de_tolerancia", "baja"): "admision_estandar",
        ("retraso_leve", "alta"): "admision_prioritaria",
        ("retraso_leve", "media"): "admision_estandar",
        ("retraso_leve", "baja"): "recepcion_fin_turno",
        ("retraso_grave", "alta"): "reprogramacion_urgente",
        ("retraso_grave", "media"): "recepcion_fin_turno",
        ("retraso_grave", "baja"): "rechazo_o_cancelacion",
        ("no_presentado", "alta"): "reprogramacion_urgente",
        ("no_presentado", "media"): "rechazo_o_cancelacion",
        ("no_presentado", "baja"): "rechazo_o_cancelacion",
    }
)

_TEXTOS_ESTADO: MappingProxyType[str, str] = MappingProxyType(
    {
        "a_tiempo": "Llegó a la hora acordada",
        "dentro_de_tolerancia": "Llegó tarde, pero dentro de los minutos de tolerancia",
        "retraso_leve": "Llegó tarde (hasta 30 min después de la tolerancia)",
        "retraso_grave": "Llegó muy tarde (más de 30 min después de la tolerancia)",
        "no_presentado": "La empresa no llegó a su cita",
    }
)

_TEXTOS_ACCION: MappingProxyType[str, str] = MappingProxyType(
    {
        "admision_prioritaria": "recibir la carga primero",
        "admision_estandar": "recibir la carga en orden normal",
        "reprogramacion_urgente": "darle una nueva hora urgente",
        "recepcion_fin_turno": "recibirla al final del día",
        "rechazo_o_cancelacion": "no recibir la carga y cancelar la cita",
    }
)


@lru_cache(maxsize=256)
def parsear_hora_a_minutos(hora_texto: str) -> int:
    """Convierte una hora 'HH:MM' válida en minutos acumulados desde 00:00."""
    if not isinstance(hora_texto, str):
        raise TypeError("La hora debe ser una cadena con formato HH:MM.")

    texto = hora_texto.strip()
    partes = texto.split(":")
    if len(partes) != 2 or len(partes[0]) != 2 or len(partes[1]) != 2:
        raise ValueError(
            f"Formato de hora inválido: '{hora_texto}'. Use HH:MM (00:00 a 23:59)."
        )

    horas_txt, minutos_txt = partes
    if not (horas_txt.isdigit() and minutos_txt.isdigit()):
        raise ValueError(
            f"Formato de hora inválido: '{hora_texto}'. Use HH:MM (00:00 a 23:59)."
        )

    horas = int(horas_txt)
    minutos = int(minutos_txt)
    if not (0 <= horas <= 23 and 0 <= minutos <= 59):
        raise ValueError(
            f"Hora fuera de rango: '{hora_texto}'. Use valores entre 00:00 y 23:59."
        )

    return horas * 60 + minutos


def calcular_minutos_retraso(
    hora_cita: str,
    hora_llegada: str | None,
    no_presentado: bool = False,
) -> int:
    """Calcula los minutos de tardanza respecto a la hora de cita."""
    minutos_cita = parsear_hora_a_minutos(hora_cita)
    if no_presentado or hora_llegada is None:
        return 0
    minutos_llegada = parsear_hora_a_minutos(hora_llegada)
    return max(0, minutos_llegada - minutos_cita)


def calcular_minutos_exceso(minutos_retraso: int, tolerancia_minutos: int) -> int:
    """Calcula los minutos que exceden la tolerancia contractual del proveedor."""
    return max(0, minutos_retraso - max(0, tolerancia_minutos))


def clasificar_estado_arribo(
    hora_cita: str,
    hora_llegada: str | None,
    tolerancia_minutos: int,
    no_presentado: bool = False,
) -> str:
    """Clasifica el arribo usando encaje de patrones (match/case) e intervalos."""
    minutos_retraso = calcular_minutos_retraso(hora_cita, hora_llegada, no_presentado)
    minutos_exceso = calcular_minutos_exceso(minutos_retraso, tolerancia_minutos)

    match (no_presentado or hora_llegada is None, minutos_retraso, minutos_exceso):
        case (True, _, _):
            return "no_presentado"
        case (False, retraso, _) if pertenece_intervalo(retraso, INTERVALO_A_TIEMPO):
            return "a_tiempo"
        case (False, _, 0):
            return "dentro_de_tolerancia"
        case (False, _, exceso) if pertenece_intervalo(exceso, INTERVALO_RETRASO_LEVE):
            return "retraso_leve"
        case (False, _, exceso) if pertenece_intervalo(exceso, INTERVALO_RETRASO_GRAVE):
            return "retraso_grave"
        case _:
            return "retraso_grave"


@lru_cache(maxsize=64)
def determinar_accion_operativa(estado_arribo: str, criticidad: str) -> str:
    """Resuelve la acción operativa en almacén desde la matriz declarativa SLA."""
    if estado_arribo not in ESTADOS_ARRIBO:
        raise ValueError(f"Estado de arribo no reconocido: '{estado_arribo}'.")
    if criticidad not in CRITICIDADES_VALIDAS:
        raise ValueError(
            f"Criticidad inválida: '{criticidad}'. Valores válidos: alta, media, baja."
        )
    return REGLAS_ACCION_OPERATIVA[(estado_arribo, criticidad)]


def explicar_regla_operativa(
    estado_arribo: str,
    criticidad: str,
    accion_operativa: str,
) -> str:
    """Genera una explicación breve y legible de la regla SLA aplicada."""
    if estado_arribo not in ESTADOS_ARRIBO:
        raise ValueError(f"Estado de arribo no reconocido: '{estado_arribo}'.")
    if criticidad not in CRITICIDADES_VALIDAS:
        raise ValueError(f"Criticidad inválida: '{criticidad}'.")
    if accion_operativa not in ACCIONES_OPERATIVAS:
        raise ValueError(f"Acción operativa no reconocida: '{accion_operativa}'.")

    detalle_estado = _TEXTOS_ESTADO[estado_arribo]
    detalle_accion = _TEXTOS_ACCION[accion_operativa]
    return (
        f"{detalle_estado} y el pedido tiene urgencia {criticidad}; "
        f"por eso se debe {detalle_accion}."
    )


def es_incidencia_sla(estado_arribo: str) -> bool:
    """Indica si el estado representa una incidencia o incumplimiento SLA."""
    return estado_arribo in ESTADOS_INCIDENCIA


def es_cumplimiento_sla(estado_arribo: str) -> bool:
    """Verifica cumplimiento SLA mediante negación por fallo sobre incidencias."""
    return estado_arribo in ESTADOS_ARRIBO and not es_incidencia_sla(estado_arribo)


def _generar_ventanas_infinitas(
    hora_inicio: str,
    paso_minutos: int = 15,
) -> Iterator[str]:
    """Generador perezoso infinito de ventanas horarias HH:MM bajo demanda."""
    if paso_minutos <= 0:
        raise ValueError("El paso entre ventanas debe ser mayor a cero minutos.")
    actual = parsear_hora_a_minutos(hora_inicio)
    while True:
        total_dia = actual % 1440
        horas, minutos = divmod(total_dia, 60)
        yield f"{horas:02d}:{minutos:02d}"
        actual += paso_minutos


def sugerir_ventanas_reprogramacion(
    hora_base: str,
    paso_minutos: int = 15,
    cantidad: int = 4,
) -> tuple[str, ...]:
    """Sugiere ventanas futuras usando evaluación perezosa sobre flujo infinito."""
    if cantidad <= 0:
        return ()
    flujo = _generar_ventanas_infinitas(hora_base.strip(), paso_minutos)
    return tuple(islice(flujo, 1, 1 + cantidad))
