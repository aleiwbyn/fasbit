% ==============================================================================
% FASBIT - Planificador Integral de Tareas de Abastecimiento
% Coordina priorización por stock, selección de ruta óptima y asignación de muelle
% evitando colapsos en zonas de recepción y errores de posicionamiento.
% ==============================================================================

% Prioriza pedidos: primero categorías con riesgo de quiebre de stock, luego plazo más próximo
obtener_pedidos_priorizados(PedidosOrdenados) :-
    findall(
        clave(PrioridadStock, PlazoMaximo, IdPedido)-pedido(
            IdPedido, IdProveedor, Categoria, Cantidad, VolumenM3,
            HoraSalida, VentanaInicio, PlazoMaximo, ZonaHabitual, RutaHabitual
        ),
        (
            pedido_entrega(
                IdPedido, IdProveedor, Categoria, Cantidad, VolumenM3,
                HoraSalida, VentanaInicio, PlazoMaximo, ZonaHabitual, RutaHabitual
            ),
            inventario_producto(Categoria, StockInicial, _, _, _),
            nivel_criticidad_stock(Categoria, StockInicial, _, PrioridadStock)
        ),
        Pares
    ),
    keysort(Pares, ParesOrdenados),
    extraer_valores_pares(ParesOrdenados, PedidosOrdenados).

% Busca o actualiza el stock acumulado durante la jornada de planificación
obtener_stock_acumulado(Categoria, MapaStocks, StockActual) :-
    member(stock(Categoria, StockActual), MapaStocks), !.
obtener_stock_acumulado(Categoria, _, StockActual) :-
    inventario_producto(Categoria, StockActual, _, _, _).

actualizar_stock_acumulado(Categoria, NuevoValor, [], [stock(Categoria, NuevoValor)]) :- !.
actualizar_stock_acumulado(Categoria, NuevoValor, [stock(Categoria, _) | Resto], [stock(Categoria, NuevoValor) | Resto]) :- !.
actualizar_stock_acumulado(Categoria, NuevoValor, [Otro | Resto], [Otro | RestoAct]) :-
    actualizar_stock_acumulado(Categoria, NuevoValor, Resto, RestoAct).

% ------------------------------------------------------------------------------
% Asignación Inteligente de Zona de Recepción sin Colapsos
% ------------------------------------------------------------------------------

% Prefiere zonas especializadas antes que el muelle auxiliar multiuso si están libres
peso_preferencia_zona(zona_d_multiuso, 2) :- !.
peso_preferencia_zona(_, 1).

asignar_zona_optima(
    Categoria, VolumenM3, HoraDisponible, ZonaHabitual, ReservasActivas,
    IdZonaAsignada, NombreZona, InicioDescarga, FinDescarga, EsperaMuelleMin, AccionZona
) :-
    % 1. Intentar asignación inmediata sin espera en alguna zona válida con cupo libre
    findall(
        Pref-candidato(IdZ, NomZ, Inicio, Fin),
        (
            zona_valida_entrega(IdZ, Categoria, VolumenM3),
            zona_recepcion(IdZ, NomZ, _, _, _, Duracion),
            Inicio is HoraDisponible,
            FinRaw is Inicio + Duracion,
            redondear2(FinRaw, Fin),
            zona_disponible_en_ventana(IdZ, Inicio, Fin, ReservasActivas),
            (IdZ == ZonaHabitual -> Pref = 0 ; peso_preferencia_zona(IdZ, Pref))
        ),
        CandidatosInmediatos
    ),
    CandidatosInmediatos \= [], !,
    keysort(CandidatosInmediatos, [_-candidato(IdZonaAsignada, NombreZona, InicioDescarga, FinDescarga) | _]),
    EsperaMuelleMin = 0.0,
    clasificar_accion_zona(ZonaHabitual, IdZonaAsignada, Categoria, VolumenM3, 0.0, AccionZona).

asignar_zona_optima(
    Categoria, VolumenM3, HoraDisponible, ZonaHabitual, ReservasActivas,
    IdZonaAsignada, NombreZona, InicioDescarga, FinDescarga, EsperaMuelleMin, AccionZona
) :-
    % 2. Si todas las zonas válidas están ocupadas en ese instante, reprogramar al primer hueco libre
    findall(
        InicioLibre-candidato(IdZ, NomZ, InicioLibre, FinLibre),
        (
            zona_valida_entrega(IdZ, Categoria, VolumenM3),
            zona_recepcion(IdZ, NomZ, _, _, _, Duracion),
            primer_turno_libre_zona(IdZ, HoraDisponible, Duracion, ReservasActivas, InicioLibre),
            FinRaw is InicioLibre + Duracion,
            redondear2(FinRaw, FinLibre)
        ),
        TurnosDiferidos
    ),
    keysort(TurnosDiferidos, [_-candidato(IdZonaAsignada, NombreZona, InicioDescarga, FinDescarga) | _]),
    EsperaRaw is InicioDescarga - HoraDisponible,
    redondear2(EsperaRaw, EsperaMuelleMin),
    clasificar_accion_zona(ZonaHabitual, IdZonaAsignada, Categoria, VolumenM3, EsperaMuelleMin, AccionZona).

primer_turno_libre_zona(IdZona, HoraBase, Duracion, ReservasActivas, HoraElegida) :-
    findall(
        RFin,
        (
            member(reserva(IdZona, _, RFin, _), ReservasActivas),
            RFin > HoraBase
        ),
        FinesPosteriores
    ),
    sort([HoraBase | FinesPosteriores], PuntosCandidatos),
    member(CandidatoRaw, PuntosCandidatos),
    redondear2(CandidatoRaw, HoraElegida),
    FinPrueba is HoraElegida + Duracion,
    zona_disponible_en_ventana(IdZona, HoraElegida, FinPrueba, ReservasActivas), !.

clasificar_accion_zona(ZonaHabitual, ZonaAsignada, Categoria, VolumenM3, EsperaMuelle, Accion) :-
    (   \+ zona_valida_entrega(ZonaHabitual, Categoria, VolumenM3)
    ->  Accion = corregida_zona_incompatible
    ;   ZonaHabitual \= ZonaAsignada
    ->  Accion = reasignada_evitar_colapso
    ;   EsperaMuelle > 0
    ->  Accion = turno_escalonado_sin_colapso
    ;   Accion = zona_confirmada_optima
    ).

% ------------------------------------------------------------------------------
% Ejecución del Planificador Optimizado (FASBIT)
% ------------------------------------------------------------------------------

planificar_todas_las_entregas(TareasPlanificadas) :-
    obtener_pedidos_priorizados(Pedidos),
    planificar_lote(Pedidos, [], [], TareasPlanificadas).

planificar_lote([], _, _, []).
planificar_lote(
    [pedido(IdPedido, IdProveedor, Categoria, Cantidad, VolumenM3, HoraSalida, VentanaInicio, PlazoMaximo, ZonaHabitual, _) | Resto],
    ReservasActivas, MapaStocks,
    [TareaDict | TareasResto]
) :-
    proveedor(IdProveedor, NombreProveedor, NodoOrigen, MultaPorMinuto),
    obtener_stock_acumulado(Categoria, MapaStocks, StockAntes),
    nivel_criticidad_stock(Categoria, StockAntes, EstadoStock, PrioridadNum),
    validar_capacidad_almacen(Categoria, StockAntes, Cantidad, DecisionAlmacen, CantidadAceptada, UnidadesExceso),
    ruta_optima_entrega(
        NodoOrigen, almacen_central, HoraSalida, VentanaInicio, PlazoMaximo, MultaPorMinuto,
        RutaOptima, NumRutasAlternativas
    ),
    HoraLlegada = RutaOptima.hora_llegada_min,
    HoraListaDescargaRaw is max(HoraLlegada, VentanaInicio),
    redondear2(HoraListaDescargaRaw, HoraListaDescarga),
    (   CantidadAceptada > 0
    ->  VolumenEfectivo is round((VolumenM3 * (CantidadAceptada / Cantidad)) * 100) / 100,
        asignar_zona_optima(
            Categoria, VolumenEfectivo, HoraListaDescarga, ZonaHabitual, ReservasActivas,
            ZonaAsignada, NombreZona, InicioDescarga, FinDescarga, EsperaMuelleMin, AccionZona
        ),
        NuevasReservas = [reserva(ZonaAsignada, InicioDescarga, FinDescarga, IdPedido) | ReservasActivas]
    ;   VolumenEfectivo = 0.0,
        ZonaAsignada = sin_descarga,
        NombreZona = 'Sin descarga (Almacen al limite)',
        InicioDescarga = HoraListaDescarga,
        FinDescarga = HoraListaDescarga,
        EsperaMuelleMin = 0.0,
        AccionZona = descarga_omitida_tope_stock,
        NuevasReservas = ReservasActivas
    ),
    StockDespues is StockAntes + CantidadAceptada,
    actualizar_stock_acumulado(Categoria, StockDespues, MapaStocks, NuevoMapaStocks),
    TareaDict = _{
        id_pedido: IdPedido,
        id_proveedor: IdProveedor,
        nombre_proveedor: NombreProveedor,
        origen: NodoOrigen,
        categoria: Categoria,
        prioridad_stock: PrioridadNum,
        estado_stock_previo: EstadoStock,
        stock_antes: StockAntes,
        stock_despues: StockDespues,
        cantidad_solicitada: Cantidad,
        cantidad_aceptada: CantidadAceptada,
        unidades_exceso_evitadas: UnidadesExceso,
        decision_almacen: DecisionAlmacen,
        volumen_efectivo_m3: VolumenEfectivo,
        ventana_inicio_min: VentanaInicio,
        plazo_maximo_min: PlazoMaximo,
        zona_habitual_proveedor: ZonaHabitual,
        zona_asignada: ZonaAsignada,
        nombre_zona_asignada: NombreZona,
        accion_zona: AccionZona,
        inicio_descarga_min: InicioDescarga,
        fin_descarga_min: FinDescarga,
        espera_muelle_min: EsperaMuelleMin,
        rutas_evaluadas: NumRutasAlternativas,
        ruta: RutaOptima,
        costo_sobrealmacenamiento_soles: 0.0,
        costo_operativo_total_soles: RutaOptima.costo_total_ruta_soles
    },
    planificar_lote(Resto, NuevasReservas, NuevoMapaStocks, TareasResto).

% ------------------------------------------------------------------------------
% Evaluación del Escenario Base (Sin Planificador - Comportamiento Habitual)
% Permite simular retrasos, errores de zona, colapsos de muelle y sobre-stock.
% ------------------------------------------------------------------------------

evaluar_escenario_sin_planificador(ResultadosBase) :-
    findall(
        pedido(IdPedido, IdProveedor, Categoria, Cantidad, VolumenM3, HoraSalida, VentanaInicio, PlazoMaximo, ZonaHabitual, RutaHabitual),
        pedido_entrega(IdPedido, IdProveedor, Categoria, Cantidad, VolumenM3, HoraSalida, VentanaInicio, PlazoMaximo, ZonaHabitual, RutaHabitual),
        Pedidos
    ),
    simular_lote_habitual(Pedidos, [], [], ResultadosBase).

simular_lote_habitual([], _, _, []).
simular_lote_habitual(
    [pedido(IdPedido, IdProveedor, Categoria, Cantidad, VolumenM3, HoraSalida, VentanaInicio, PlazoMaximo, ZonaHabitual, RutaHabitual) | Resto],
    OcupacionHabitual, MapaStocks,
    [ResultadoDict | RestoResultados]
) :-
    proveedor(IdProveedor, NombreProveedor, NodoOrigen, MultaPorMinuto),
    evaluar_ruta_fija(RutaHabitual, HoraSalida, Tramos, DistKm, TiempoMin, CostoTransp),
    HoraLlegadaRaw is HoraSalida + TiempoMin,
    redondear2(HoraLlegadaRaw, HoraLlegada),
    evaluar_cumplimiento_plazo(
        HoraLlegada, VentanaInicio, PlazoMaximo, MultaPorMinuto,
        EstadoPuntualidad, MinRetraso, MinEspera, CostoMulta
    ),
    zona_recepcion(ZonaHabitual, NombreZonaHab, _, CapSimultanea, _, DuracionBase),
    InicioIntento is max(HoraLlegada, VentanaInicio),
    FinIntento is InicioIntento + DuracionBase,
    (   zona_valida_entrega(ZonaHabitual, Categoria, VolumenM3)
    ->  ErrorPosicionamiento = false,
        CostoReprocesoZona = 0.0
    ;   ErrorPosicionamiento = true,
        CostoReprocesoZona = 45.0   % Sobrecosto operativo por maniobra y reubicación de muelle incorrecto
    ),
    contar_ocupacion_zona(ZonaHabitual, InicioIntento, FinIntento, OcupacionHabitual, VehiculosSolapados),
    (   VehiculosSolapados >= CapSimultanea
    ->  ColapsoZona = true,
        CostoCongestionMuelle = 35.0
    ;   ColapsoZona = false,
        CostoCongestionMuelle = 0.0
    ),
    obtener_stock_acumulado(Categoria, MapaStocks, StockAntes),
    inventario_producto(Categoria, _, _, CapacidadMax, _),
    EspacioLibre is max(0, CapacidadMax - StockAntes),
    UnidadesExceso is max(0, Cantidad - EspacioLibre),
    CostoSobreStockRaw is UnidadesExceso * 1.85,
    redondear2(CostoSobreStockRaw, CostoSobreStock),
    StockDespues is min(CapacidadMax, StockAntes + Cantidad),
    actualizar_stock_acumulado(Categoria, StockDespues, MapaStocks, NuevoMapaStocks),
    CostoTotalRaw is CostoTransp + CostoMulta + CostoReprocesoZona + CostoCongestionMuelle + CostoSobreStock,
    redondear2(CostoTotalRaw, CostoTotal),
    NuevasOcupaciones = [reserva(ZonaHabitual, InicioIntento, FinIntento, IdPedido) | OcupacionHabitual],
    RutaDict = _{
        nodos: RutaHabitual,
        tramos: Tramos,
        distancia_km: DistKm,
        tiempo_transito_min: TiempoMin,
        hora_salida_min: HoraSalida,
        hora_llegada_min: HoraLlegada,
        estado_puntualidad: EstadoPuntualidad,
        minutos_retraso: MinRetraso,
        minutos_espera_ventana: MinEspera,
        costo_transporte_soles: CostoTransp,
        costo_multa_soles: CostoMulta,
        costo_total_ruta_soles: CostoTotal
    },
    ResultadoDict = _{
        id_pedido: IdPedido,
        id_proveedor: IdProveedor,
        nombre_proveedor: NombreProveedor,
        origen: NodoOrigen,
        categoria: Categoria,
        cantidad_solicitada: Cantidad,
        unidades_exceso_almacen: UnidadesExceso,
        ventana_inicio_min: VentanaInicio,
        plazo_maximo_min: PlazoMaximo,
        zona_intentada: ZonaHabitual,
        nombre_zona_intentada: NombreZonaHab,
        error_posicionamiento_zona: ErrorPosicionamiento,
        colapso_zona_recepcion: ColapsoZona,
        inicio_recepcion_min: InicioIntento,
        fin_recepcion_min: FinIntento,
        ruta: RutaDict,
        costo_reproceso_zona_soles: CostoReprocesoZona,
        costo_congestion_muelle_soles: CostoCongestionMuelle,
        costo_sobrealmacenamiento_soles: CostoSobreStock,
        costo_operativo_total_soles: CostoTotal
    },
    simular_lote_habitual(Resto, NuevasOcupaciones, NuevoMapaStocks, RestoResultados).

