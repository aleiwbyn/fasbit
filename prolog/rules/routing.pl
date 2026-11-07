% ==============================================================================
% FASBIT - Motor de Inferencia y Optimización de Rutas en Grafos
% Calcula rutas libres de ciclos, tiempos reales con tráfico y ruta óptima.
% ==============================================================================

% Evalúa un tramo individual considerando el tráfico vigente al llegar al nodo
evaluar_tramo_con_trafico(
    Origen, Destino, HoraActualMin,
    TramoInfo, DistanciaKm, TiempoRealMin, CostoRealSoles
) :-
    tramo(Origen, Destino, DistanciaKm, TiempoBase, CostoBase),
    nivel_trafico_efectivo(Origen, Destino, HoraActualMin, NivelTrafico),
    factor_trafico(NivelTrafico, FactorTiempo),
    factor_costo_trafico(NivelTrafico, FactorCosto),
    TiempoRaw is TiempoBase * FactorTiempo,
    CostoRaw is CostoBase * FactorCosto,
    redondear2(TiempoRaw, TiempoRealMin),
    redondear2(CostoRaw, CostoRealSoles),
    TramoInfo = _{
        origen: Origen,
        destino: Destino,
        distancia_km: DistanciaKm,
        tiempo_base_min: TiempoBase,
        tiempo_real_min: TiempoRealMin,
        costo_soles: CostoRealSoles,
        trafico: NivelTrafico
    }.

% Búsqueda en profundidad libre de ciclos (DFS con propagación temporal dinámica)
buscar_camino(
    Origen, Destino, HoraSalidaMin,
    RutaNodos, DetalleTramos, DistanciaTotalKm, TiempoTotalMin, CostoTransporteSoles
) :-
    dfs_ruta(
        Origen, Destino, HoraSalidaMin, [Origen],
        RutaNodos, DetalleTramos, DistRaw, TiempoRaw, CostoRaw
    ),
    redondear2(DistRaw, DistanciaTotalKm),
    redondear2(TiempoRaw, TiempoTotalMin),
    redondear2(CostoRaw, CostoTransporteSoles).

dfs_ruta(Destino, Destino, _, _, [Destino], [], 0.0, 0.0, 0.0) :- !.
dfs_ruta(
    Actual, Destino, HoraActual, Visitados,
    [Actual | RestoNodos], [TramoInfo | RestoTramos],
    DistTotal, TiempoTotal, CostoTotal
) :-
    evaluar_tramo_con_trafico(Actual, Siguiente, HoraActual, TramoInfo, DistP, TiempoP, CostoP),
    \+ member(Siguiente, Visitados),
    NuevaHora is HoraActual + TiempoP,
    dfs_ruta(
        Siguiente, Destino, NuevaHora, [Siguiente | Visitados],
        RestoNodos, RestoTramos, DistResto, TiempoResto, CostoResto
    ),
    DistTotal is DistP + DistResto,
    TiempoTotal is TiempoP + TiempoResto,
    CostoTotal is CostoP + CostoResto.

% Evalúa una ruta fija (ej. ruta habitual no optimizada de un proveedor)
evaluar_ruta_fija([_], _, [], 0.0, 0.0, 0.0) :- !.
evaluar_ruta_fija(
    [NodoA, NodoB | Resto], HoraActual,
    [TramoInfo | RestoTramos], DistTotal, TiempoTotal, CostoTotal
) :-
    evaluar_tramo_con_trafico(NodoA, NodoB, HoraActual, TramoInfo, DistP, TiempoP, CostoP),
    NuevaHora is HoraActual + TiempoP,
    evaluar_ruta_fija([NodoB | Resto], NuevaHora, RestoTramos, DistR, TiempoR, CostoR),
    DistRaw is DistP + DistR,
    TiempoRaw is TiempoP + TiempoR,
    CostoRaw is CostoP + CostoR,
    redondear2(DistRaw, DistTotal),
    redondear2(TiempoRaw, TiempoTotal),
    redondear2(CostoRaw, CostoTotal).

% Calcula función objetivo compuesta: prioriza cumplimiento de plazo + mínimo costo integral
puntaje_optimizacion(CostoTransporte, CostoMulta, TiempoTotalMin, EstadoPuntualidad, Puntaje) :-
    (EstadoPuntualidad == retrasado -> PenalidadSLA = 60.0 ; PenalidadSLA = 0.0),
    Raw is CostoTransporte + CostoMulta + PenalidadSLA + (TiempoTotalMin * 0.35),
    redondear2(Raw, Puntaje).

% Obtiene todas las rutas factibles ordenadas de mejor a peor según puntaje
rutas_ordenadas_entrega(
    Origen, Destino, HoraSalidaMin, VentanaInicioMin, PlazoMaximoMin, MultaPorMinuto,
    RutasOrdenadas
) :-
    findall(
        Puntaje-RutaDict,
        (
            buscar_camino(
                Origen, Destino, HoraSalidaMin,
                Nodos, Tramos, DistKm, TiempoMin, CostoTransp
            ),
            HoraLlegadaRaw is HoraSalidaMin + TiempoMin,
            redondear2(HoraLlegadaRaw, HoraLlegada),
            evaluar_cumplimiento_plazo(
                HoraLlegada, VentanaInicioMin, PlazoMaximoMin, MultaPorMinuto,
                EstadoPuntualidad, MinRetraso, MinEspera, CostoMulta
            ),
            CostoTotalRaw is CostoTransp + CostoMulta,
            redondear2(CostoTotalRaw, CostoTotal),
            puntaje_optimizacion(CostoTransp, CostoMulta, TiempoMin, EstadoPuntualidad, Puntaje),
            RutaDict = _{
                nodos: Nodos,
                tramos: Tramos,
                distancia_km: DistKm,
                tiempo_transito_min: TiempoMin,
                hora_salida_min: HoraSalidaMin,
                hora_llegada_min: HoraLlegada,
                estado_puntualidad: EstadoPuntualidad,
                minutos_retraso: MinRetraso,
                minutos_espera_ventana: MinEspera,
                costo_transporte_soles: CostoTransp,
                costo_multa_soles: CostoMulta,
                costo_total_ruta_soles: CostoTotal,
                puntaje_optimizacion: Puntaje
            }
        ),
        Pares
    ),
    keysort(Pares, ParesOrdenados),
    extraer_valores_pares(ParesOrdenados, RutasOrdenadas).

extraer_valores_pares([], []).
extraer_valores_pares([_-Valor | Resto], [Valor | ValoresResto]) :-
    extraer_valores_pares(Resto, ValoresResto).

% Selecciona la ruta óptima para una entrega específica
ruta_optima_entrega(
    Origen, Destino, HoraSalidaMin, VentanaInicioMin, PlazoMaximoMin, MultaPorMinuto,
    MejorRuta, CantidadAlternativas
) :-
    rutas_ordenadas_entrega(
        Origen, Destino, HoraSalidaMin, VentanaInicioMin, PlazoMaximoMin, MultaPorMinuto,
        Rutas
    ),
    Rutas = [MejorRuta | _],
    length(Rutas, CantidadAlternativas).

