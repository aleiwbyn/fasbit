"""Repositorio JSON para lectura y escritura de entregas programadas."""

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from fasbit.modelos.entrega_modelo import Entrega
from fasbit.modelos.proveedor_modelo import Proveedor


def _diccionario_a_proveedor(datos: dict[str, Any]) -> Proveedor:
    """Convierte un diccionario JSON en una instancia inmutable de Proveedor."""
    return Proveedor(
        id_proveedor=str(datos["id_proveedor"]),
        nombre=str(datos["nombre"]),
        ruc=str(datos["ruc"]),
        tolerancia_minutos=int(datos["tolerancia_minutos"]),
        tarifa_minuto_soles=float(datos["tarifa_minuto_soles"]),
        penalidad_inasistencia_soles=float(datos["penalidad_inasistencia_soles"]),
    )


def _diccionario_a_entrega(datos: dict[str, Any]) -> Entrega:
    """Convierte un diccionario JSON en una instancia inmutable de Entrega."""
    hora_llegada = datos.get("hora_llegada")
    return Entrega(
        id_entrega=str(datos["id_entrega"]),
        codigo_orden=str(datos["codigo_orden"]),
        proveedor=_diccionario_a_proveedor(datos["proveedor"]),
        hora_cita=str(datos["hora_cita"]),
        hora_llegada=str(hora_llegada) if hora_llegada is not None else None,
        criticidad=str(datos["criticidad"]),
        no_presentado=bool(datos.get("no_presentado", False)),
        observacion=str(datos.get("observacion", "")),
    )


def _entrega_a_diccionario(entrega: Entrega) -> dict[str, Any]:
    """Serializa una entrega inmutable y su proveedor a diccionario JSON."""
    proveedor = entrega.proveedor
    return {
        "id_entrega": entrega.id_entrega,
        "codigo_orden": entrega.codigo_orden,
        "proveedor": {
            "id_proveedor": proveedor.id_proveedor,
            "nombre": proveedor.nombre,
            "ruc": proveedor.ruc,
            "tolerancia_minutos": proveedor.tolerancia_minutos,
            "tarifa_minuto_soles": proveedor.tarifa_minuto_soles,
            "penalidad_inasistencia_soles": proveedor.penalidad_inasistencia_soles,
        },
        "hora_cita": entrega.hora_cita,
        "hora_llegada": entrega.hora_llegada,
        "criticidad": entrega.criticidad,
        "no_presentado": entrega.no_presentado,
        "observacion": entrega.observacion,
    }


def cargar_entregas(ruta_archivo: Path) -> tuple[Entrega, ...]:
    """Lee el archivo JSON de entregas y devuelve una tupla inmutable."""
    if not ruta_archivo.exists():
        return ()
    contenido = ruta_archivo.read_text(encoding="utf-8").strip()
    if not contenido:
        return ()
    registros: list[dict[str, Any]] = json.loads(contenido)
    return tuple(map(_diccionario_a_entrega, registros))


def guardar_entregas(ruta_archivo: Path, entregas: Iterable[Entrega]) -> None:
    """Persiste la colección de entregas en formato JSON UTF-8 ordenado."""
    ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
    ordenadas = sorted(entregas, key=lambda item: item.id_entrega)
    datos = [_entrega_a_diccionario(item) for item in ordenadas]
    ruta_archivo.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
