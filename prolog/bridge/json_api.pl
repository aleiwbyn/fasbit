% ==============================================================================
% FASBIT - Puente JSON estructurado (SWI-Prolog <-> Python)
% Lee peticiones JSON por entrada estándar y responde en JSON estándar.
% ==============================================================================

:- use_module(library(http/json)).

% Punto de entrada principal para llamadas desde Python por stdin/stdout
procesar_peticion_stdin :-
    catch(
        (
            json_read_dict(current_input, Peticion, [value_string_as(atom)]),
            ejecutar_accion(Peticion, Respuesta),
            json_write_dict(current_output, Respuesta, [width(0)]),
            nl
        ),
        Error,
        (
            term_string(Error, MensajeError),
            json_write_dict(current_output, _{status: error, message: MensajeError}, [width(0)]),
            nl
        )
    ).

% Aplicación limpia de overrides dinámicos para escenarios de simulación
aplicar_overrides(Peticion) :-
    retractall(trafico_override(_, _, _)),
    (   get_dict(traffic_overrides, Peticion, ListaTrafico)
    ->  forall(
            member(T, ListaTrafico),
            assertz(trafico_override(T.origen, T.destino, T.nivel))
        )
    ;   true
    ),
    (   get_dict(stock_overrides, Peticion, ListaStock)
    ->  forall(
            member(S, ListaStock),
            actualizar_inventario_dinamico(S)
        )
    ;   true
    ),
    (   get_dict(custom_orders, Peticion, ListaPedidos),
        ListaPedidos \= []
    ->  retractall(pedido_entrega(_, _, _, _, _, _, _, _, _, _)),
        forall(
            member(P, ListaPedidos),
            assertz(pedido_entrega(
                P.id_pedido, P.id_proveedor, P.categoria, P.cantidad, P.volumen_m3,
                P.hora_salida_min, P.ventana_inicio_min, P.plazo_maximo_min,
                P.zona_habitual, P.ruta_habitual
            ))
        )
    ;   true
    ).

actualizar_inventario_dinamico(S) :-
    Categoria = S.categoria,
    (   inventario_producto(Categoria, StockAnt, MinAnt, MaxAnt, VolAnt)
    ->  retractall(inventario_producto(Categoria, _, _, _, _)),
        (get_dict(stock_actual, S, NuevoStock) -> true ; NuevoStock = StockAnt),
        (get_dict(stock_minimo, S, NuevoMin)   -> true ; NuevoMin = MinAnt),
        (get_dict(capacidad_maxima, S, NuevoMax) -> true ; NuevoMax = MaxAnt),
        assertz(inventario_producto(Categoria, NuevoStock, NuevoMin, NuevoMax, VolAnt))
    ;   true
    ).

% ------------------------------------------------------------------------------
% Despachador de acciones JSON
% ------------------------------------------------------------------------------

ejecutar_accion(Peticion, _{status: ok, engine: swi_prolog, modules_loaded: true}) :-
    Peticion.action == health, !.

ejecutar_accion(Peticion, Respuesta) :-
    Peticion.action == inspect_state, !,
    aplicar_overrides(Peticion),
    exportar_ubicaciones(Ubicaciones),
    exportar_tramos(Tramos),
    exportar_zonas(Zonas),
    exportar_inventario(Inventario),
    exportar_proveedores(Proveedores),
    exportar_pedidos(Pedidos),
    Respuesta = _{
        status: ok,
        ubicaciones: Ubicaciones,
        tramos: Tramos,
        zonas_recepcion: Zonas,
        inventario: Inventario,
        proveedores: Proveedores,
        pedidos: Pedidos
    }.

ejecutar_accion(Peticion, Respuesta) :-
    Peticion.action == find_routes, !,
    aplicar_overrides(Peticion),
    rutas_ordenadas_entrega(
        Peticion.origen,
        Peticion.destino,
        Peticion.hora_salida_min,
        Peticion.ventana_inicio_min,
        Peticion.plazo_maximo_min,
        Peticion.multa_por_minuto,
        Rutas
    ),
    length(Rutas, Total),
    (Rutas = [Mejor | _] -> MejorRuta = Mejor ; MejorRuta = null),
    Respuesta = _{
        status: ok,
        total_alternativas: Total,
        ruta_optima: MejorRuta,
        alternativas: Rutas
    }.

ejecutar_accion(Peticion, Respuesta) :-
    Peticion.action == plan_tasks, !,
    aplicar_overrides(Peticion),
    planificar_todas_las_entregas(Tareas),
    Respuesta = _{
        status: ok,
        tareas_planificadas: Tareas
    }.

ejecutar_accion(Peticion, Respuesta) :-
    Peticion.action == compare_simulation, !,
    aplicar_overrides(Peticion),
    evaluar_escenario_sin_planificador(EscenarioBase),
    planificar_todas_las_entregas(EscenarioOptimizado),
    Respuesta = _{
        status: ok,
        escenario_base: EscenarioBase,
        escenario_optimizado: EscenarioOptimizado
    }.

ejecutar_accion(Peticion, _{status: error, message: 'Accion no reconocida', action: Accion}) :-
    (get_dict(action, Peticion, Accion) -> true ; Accion = desconocida).

% ------------------------------------------------------------------------------
% Predicados auxiliares de exportación del estado de la Base de Conocimientos
% ------------------------------------------------------------------------------

exportar_ubicaciones(Lista) :-
    findall(
        _{id: Id, nombre: Nombre, tipo: Tipo, x: X, y: Y},
        ubicacion(Id, Nombre, Tipo, X, Y),
        Lista
    ).

exportar_tramos(Lista) :-
    findall(
        _{
            origen: O, destino: D,
            distancia_km: Dist, tiempo_base_min: TBase, costo_base_soles: CBase
        },
        tramo(O, D, Dist, TBase, CBase),
        Lista
    ).

exportar_zonas(Lista) :-
    findall(
        _{
            id_zona: IdZ, nombre: Nom,
            categorias_permitidas: Cats,
            capacidad_simultanea: CapSim,
            capacidad_max_volumen_m3: CapVol,
            tiempo_descarga_min: TDesc
        },
        zona_recepcion(IdZ, Nom, Cats, CapSim, CapVol, TDesc),
        Lista
    ).

exportar_inventario(Lista) :-
    findall(
        _{
            categoria: Cat,
            stock_actual: SAct,
            stock_minimo: SMin,
            capacidad_maxima: CapMax,
            volumen_unitario_m3: VolU,
            estado_criticidad: Estado
        },
        (
            inventario_producto(Cat, SAct, SMin, CapMax, VolU),
            nivel_criticidad_stock(Cat, SAct, Estado, _)
        ),
        Lista
    ).

exportar_proveedores(Lista) :-
    findall(
        _{
            id_proveedor: IdP,
            nombre: Nom,
            origen: Orig,
            multa_soles_por_min: Multa
        },
        proveedor(IdP, Nom, Orig, Multa),
        Lista
    ).

exportar_pedidos(Lista) :-
    findall(
        _{
            id_pedido: IdPed,
            id_proveedor: IdProv,
            categoria: Cat,
            cantidad: Cant,
            volumen_m3: Vol,
            hora_salida_min: HSal,
            ventana_inicio_min: VIni,
            plazo_maximo_min: PMax,
            zona_habitual: ZHab,
            ruta_habitual: RHab
        },
        pedido_entrega(IdPed, IdProv, Cat, Cant, Vol, HSal, VIni, PMax, ZHab, RHab),
        Lista
    ).

