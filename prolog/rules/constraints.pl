% ==============================================================================
% FASBIT - Reglas de Restricciones Lógicas
% Valida zonas de recepción, capacidad volumétrica, plazos horarios y almacén.
% ==============================================================================

redondear2(Valor, Redondeado) :-
    Redondeado is round(Valor * 100) / 100.

% ------------------------------------------------------------------------------
% 1. Restricciones de Posicionamiento y Capacidad en Zonas de Recepción
% ------------------------------------------------------------------------------

zona_compatible_categoria(IdZona, Categoria) :-
    zona_recepcion(IdZona, _, CategoriasPermitidas, _, _, _),
    member(Categoria, CategoriasPermitidas).

zona_soporta_volumen(IdZona, VolumenM3) :-
    zona_recepcion(IdZona, _, _, _, CapMaxVolumen, _),
    VolumenM3 =< CapMaxVolumen.

zona_valida_entrega(IdZona, Categoria, VolumenM3) :-
    zona_compatible_categoria(IdZona, Categoria),
    zona_soporta_volumen(IdZona, VolumenM3).

% Verifica si dos intervalos [Inicio1, Fin1) y [Inicio2, Fin2) se solapan
intervalos_solapados(Inicio1, Fin1, Inicio2, Fin2) :-
    Inicio1 < Fin2,
    Inicio2 < Fin1.

% Cuenta cuántos vehículos ocupan simultáneamente una zona en un rango horario
contar_ocupacion_zona(IdZona, Inicio, Fin, ReservasActivas, Ocupados) :-
    findall(
        IdPed,
        (
            member(reserva(IdZona, RInicio, RFin, IdPed), ReservasActivas),
            intervalos_solapados(Inicio, Fin, RInicio, RFin)
        ),
        Solapados
    ),
    length(Solapados, Ocupados).

zona_disponible_en_ventana(IdZona, Inicio, Fin, ReservasActivas) :-
    zona_recepcion(IdZona, _, _, CapSimultanea, _, _),
    contar_ocupacion_zona(IdZona, Inicio, Fin, ReservasActivas, Ocupados),
    Ocupados < CapSimultanea.

% ------------------------------------------------------------------------------
% 2. Restricciones de Puntualidad y Ventanas de Entrega
% ------------------------------------------------------------------------------

evaluar_cumplimiento_plazo(
    HoraLlegada, VentanaInicio, PlazoMaximo, MultaPorMinuto,
    EstadoPuntualidad, MinutosRetraso, MinutosEsperaApertura, CostoMulta
) :-
    (   HoraLlegada =< PlazoMaximo
    ->  EstadoPuntualidad = a_tiempo,
        MinutosRetraso = 0.0,
        CostoMulta = 0.0,
        EsperaRaw is max(0.0, VentanaInicio - HoraLlegada),
        redondear2(EsperaRaw, MinutosEsperaApertura)
    ;   EstadoPuntualidad = retrasado,
        RetrasoRaw is HoraLlegada - PlazoMaximo,
        redondear2(RetrasoRaw, MinutosRetraso),
        MultaRaw is RetrasoRaw * MultaPorMinuto,
        redondear2(MultaRaw, CostoMulta),
        MinutosEsperaApertura = 0.0
    ).

% ------------------------------------------------------------------------------
% 3. Restricciones de Stock y Capacidad de Almacenamiento
% ------------------------------------------------------------------------------

nivel_criticidad_stock(Categoria, StockActual, EstadoStock, PrioridadOrden) :-
    inventario_producto(Categoria, _, StockMinimo, _, _),
    UmbralPreventivo is StockMinimo * 1.30,
    (   StockActual < StockMinimo
    ->  EstadoStock = critico_riesgo_quiebre,
        PrioridadOrden = 1
    ;   StockActual < UmbralPreventivo
    ->  EstadoStock = alerta_preventiva,
        PrioridadOrden = 2
    ;   EstadoStock = stock_saludable,
        PrioridadOrden = 3
    ).

validar_capacidad_almacen(
    Categoria, StockActual, CantidadSolicitada,
    DecisionAlmacen, CantidadAceptada, UnidadesExceso
) :-
    inventario_producto(Categoria, _, _, CapacidadMaxima, _),
    EspacioDisponible is max(0, CapacidadMaxima - StockActual),
    (   CantidadSolicitada =< EspacioDisponible
    ->  DecisionAlmacen = recepcion_completa,
        CantidadAceptada = CantidadSolicitada,
        UnidadesExceso = 0
    ;   EspacioDisponible > 0
    ->  DecisionAlmacen = recepcion_parcial_tope_almacen,
        CantidadAceptada = EspacioDisponible,
        UnidadesExceso is CantidadSolicitada - EspacioDisponible
    ;   DecisionAlmacen = rechazado_almacen_lleno,
        CantidadAceptada = 0,
        UnidadesExceso = CantidadSolicitada
    ).

