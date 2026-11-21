"""Operaciones funcionales puras para filtrar, ordenar y actualizar entregas."""

from collections.abc import Callable, Iterable
from dataclasses import replace
from types import MappingProxyType

from fasbit.modelos.entrega_modelo import Entrega, EvaluacionEntrega
from fasbit.modelos.proveedor_modelo import CRITICIDADES_VALIDAS, Proveedor
from fasbit.servicios.sla_servicio import parsear_hora_a_minutos

ORDEN_CRITICIDAD: MappingProxyType[str, int] = MappingProxyType(
    {
        "alta": 1,
        "media": 2,
        "baja": 3,
    }
)


def filtrar_evaluaciones(
    evaluaciones: Iterable[EvaluacionEntrega],
    estado: str = "",
    criticidad: str = "",
    accion: str = "",
    texto_busqueda: str = "",
) -> tuple[EvaluacionEntrega, ...]:
    """Filtra evaluaciones encadenando predicados puros con filter()."""
    estado_norm = estado.strip()
    criticidad_norm = criticidad.strip()
    accion_norm = accion.strip()
    termino = texto_busqueda.strip().lower()

    resultado: Iterable[EvaluacionEntrega] = evaluaciones

    if estado_norm:
        resultado = filter(lambda ev: ev.estado_arribo == estado_norm, resultado)
    if criticidad_norm:
        resultado = filter(
            lambda ev: ev.entrega.criticidad == criticidad_norm, resultado
        )
    if accion_norm:
        resultado = filter(lambda ev: ev.accion_operativa == accion_norm, resultado)
    if termino:
        resultado = filter(
            lambda ev: (
                termino in ev.entrega.codigo_orden.lower()
                or termino in ev.entrega.proveedor.nombre.lower()
                or termino in ev.entrega.proveedor.ruc.lower()
                or termino in ev.entrega.id_entrega.lower()
            ),
            resultado,
        )

    return tuple(resultado)


def _clave_ordenamiento(
    criterio: str,
) -> Callable[[EvaluacionEntrega], tuple[object, ...]]:
    """Devuelve la función clave de ordenamiento para un criterio dado."""
    claves: dict[str, Callable[[EvaluacionEntrega], tuple[object, ...]]] = {
        "cita": lambda ev: (
            parsear_hora_a_minutos(ev.entrega.hora_cita),
            ev.entrega.id_entrega,
        ),
        "retraso": lambda ev: (ev.minutos_retraso, ev.entrega.id_entrega),
        "multa": lambda ev: (ev.multa_soles, ev.entrega.id_entrega),
        "criticidad": lambda ev: (
            ORDEN_CRITICIDAD.get(ev.entrega.criticidad, 99),
            parsear_hora_a_minutos(ev.entrega.hora_cita),
        ),
        "proveedor": lambda ev: (
            ev.entrega.proveedor.nombre.lower(),
            parsear_hora_a_minutos(ev.entrega.hora_cita),
        ),
    }
    return claves.get(criterio, claves["cita"])


def ordenar_evaluaciones(
    evaluaciones: Iterable[EvaluacionEntrega],
    criterio: str = "cita",
    descendente: bool = False,
) -> tuple[EvaluacionEntrega, ...]:
    """Ordena evaluaciones usando sorted() según el criterio seleccionado."""
    funcion_clave = _clave_ordenamiento(criterio.strip().lower())
    return tuple(sorted(evaluaciones, key=funcion_clave, reverse=descendente))


def normalizar_codigo_orden(texto: str) -> str:
    """Elimina espacios y convierte a mayúsculas recursivamente."""
    if texto == "":
        return ""
    cabeza, cola = texto[0], texto[1:]
    prefijo = "" if cabeza.isspace() else cabeza.upper()
    return prefijo + normalizar_codigo_orden(cola)


def _buscar_recursivo(
    entregas: tuple[Entrega, ...],
    id_entrega: str,
) -> Entrega | None:
    """Búsqueda recursiva estructural sobre cabeza y cola de entregas."""
    if not entregas:
        return None
    cabeza, cola = entregas[0], entregas[1:]
    if cabeza.id_entrega == id_entrega:
        return cabeza
    return _buscar_recursivo(cola, id_entrega)


def buscar_entrega_por_id(
    entregas: Iterable[Entrega],
    id_entrega: str,
) -> Entrega | None:
    """Busca una entrega por su identificador mediante recursión estructural."""
    return _buscar_recursivo(tuple(entregas), id_entrega)


def actualizar_llegada_entrega(
    entrega: Entrega,
    hora_llegada: str | None,
    no_presentado: bool,
    observacion: str = "",
) -> Entrega:
    """Retorna una nueva Entrega inmutable con el arribo u omisión actualizados."""
    observacion_limpia = observacion.strip()
    if no_presentado:
        return replace(
            entrega,
            hora_llegada=None,
            no_presentado=True,
            observacion=observacion_limpia,
        )

    if hora_llegada is None or not hora_llegada.strip():
        raise ValueError(
            "Escribe a qué hora llegó o marca la casilla si no vino."
        )

    hora_limpia = hora_llegada.strip()
    parsear_hora_a_minutos(hora_limpia)
    return replace(
        entrega,
        hora_llegada=hora_limpia,
        no_presentado=False,
        observacion=observacion_limpia,
    )


def _siguiente_id_entrega(entregas_existentes: Iterable[Entrega]) -> str:
    """Calcula el siguiente identificador correlativo con formato ENT-XXX."""
    numeros = []
    for entrega in entregas_existentes:
        if entrega.id_entrega.startswith("ENT-"):
            sufijo = entrega.id_entrega[4:]
            if sufijo.isdigit():
                numeros.append(int(sufijo))
    siguiente = max(numeros, default=0) + 1
    return f"ENT-{siguiente:03d}"


def crear_entrega(
    entregas_existentes: Iterable[Entrega],
    codigo_orden: str,
    proveedor: Proveedor,
    hora_cita: str,
    hora_llegada: str | None,
    criticidad: str,
    no_presentado: bool = False,
    observacion: str = "",
) -> Entrega:
    """Valida los datos y construye una nueva Entrega inmutable."""
    orden_limpia = normalizar_codigo_orden(codigo_orden)
    if not orden_limpia:
        raise ValueError("Escribe el número de orden.")

    criticidad_limpia = criticidad.strip().lower()
    if criticidad_limpia not in CRITICIDADES_VALIDAS:
        raise ValueError(
            "Nivel de urgencia no válido. Elige alta, media o baja."
        )

    cita_limpia = hora_cita.strip()
    parsear_hora_a_minutos(cita_limpia)

    llegada_limpia: str | None
    if no_presentado:
        llegada_limpia = None
    else:
        if hora_llegada is None or not hora_llegada.strip():
            raise ValueError(
                "Escribe a qué hora llegó o marca la casilla si no vino."
            )
        llegada_limpia = hora_llegada.strip()
        parsear_hora_a_minutos(llegada_limpia)

    return Entrega(
        id_entrega=_siguiente_id_entrega(entregas_existentes),
        codigo_orden=orden_limpia,
        proveedor=proveedor,
        hora_cita=cita_limpia,
        hora_llegada=llegada_limpia,
        criticidad=criticidad_limpia,
        no_presentado=no_presentado,
        observacion=observacion.strip(),
    )


def reemplazar_entrega_en_coleccion(
    entregas: Iterable[Entrega],
    entrega_actualizada: Entrega,
) -> tuple[Entrega, ...]:
    """Devuelve una nueva tupla reemplazando la entrega coincidente por ID."""

    def _seleccionar(item: Entrega) -> Entrega:
        return (
            entrega_actualizada
            if item.id_entrega == entrega_actualizada.id_entrega
            else item
        )

    return tuple(map(_seleccionar, entregas))


def agregar_entrega_a_coleccion(
    entregas: Iterable[Entrega],
    nueva_entrega: Entrega,
) -> tuple[Entrega, ...]:
    """Devuelve una nueva tupla agregando la nueva entrega al final."""
    return tuple(entregas) + (nueva_entrega,)


def eliminar_entrega_en_coleccion(
    entregas: Iterable[Entrega],
    id_entrega: str,
) -> tuple[Entrega, ...]:
    """Devuelve una nueva tupla excluyendo la entrega indicada por ID."""
    tupla_actual = tuple(entregas)
    if buscar_entrega_por_id(tupla_actual, id_entrega) is None:
        raise ValueError(f"No se encontró la entrega '{id_entrega}'.")
    return tuple(filter(lambda item: item.id_entrega != id_entrega, tupla_actual))


def obtener_proveedores_unicos(entregas: Iterable[Entrega]) -> tuple[Proveedor, ...]:
    """Extrae proveedores únicos ordenados alfabéticamente por nombre."""
    por_id: dict[str, Proveedor] = {}
    for entrega in entregas:
        por_id[entrega.proveedor.id_proveedor] = entrega.proveedor
    return tuple(sorted(por_id.values(), key=lambda prov: prov.nombre.lower()))
