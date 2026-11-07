% ==============================================================================
% FASBIT - Base de Conocimientos: Proveedores y Órdenes de Abastecimiento
% Modela proveedores, ubicación de origen, multas por retraso y entregas.
% ==============================================================================

:- dynamic proveedor/4.
:- dynamic pedido_entrega/10.

% proveedor(IdProveedor, NombreEmpresa, UbicacionOrigen, MultaSolesPorMinuto)
proveedor(prov_pacifico,  'Frigorificos del Pacifico S.A.',     puerto_callao,     4.50).
proveedor(prov_andina,    'Distribuidora Andina de Alimentos',  parque_ind_ate,    3.20).
proveedor(prov_norte_pack,'Empaques e Insumos Norte S.A.C.',    polo_norte_indep,  2.50).
proveedor(prov_sur_ind,   'Quimica e Insumos del Sur S.A.',     centro_log_lurin,  4.80).
proveedor(prov_agro_valle,'Agroindustrias Valle Central S.A.C.',centro_log_lurin,  3.60).

% pedido_entrega(
%   IdPedido, IdProveedor, CategoriaProducto, CantidadUnidades, VolumenM3,
%   HoraSalidaMin, VentanaInicioMin, PlazoMaximoMin,
%   ZonaHabitualProveedor, RutaHabitualProveedor
% )
% Nota de tiempos: 420 = 07:00, 450 = 07:30, 480 = 08:00, 510 = 08:30, 540 = 09:00

% Pedido 1: Producto refrigerado urgente desde Callao en hora punta.
% Su ruta habitual por Javier Prado sufre tráfico crítico y llega tarde; además intenta ir a zona_b_seco por error operativo.
pedido_entrega(
    ped_001, prov_pacifico, refrigerado, 250, 30.0,
    430, 475, 500,
    zona_b_seco,
    [puerto_callao, nodo_faucett, nodo_javier_prado, almacen_central]
).

% Pedido 2: Abarrotes secos desde Ate en hora punta.
% Su ruta habitual por Carretera Central directa colapsa en hora punta; Ramiro Prialé optimiza el tiempo.
pedido_entrega(
    ped_002, prov_andina, abarrotes_secos, 350, 35.0,
    450, 465, 480,
    zona_b_seco,
    [parque_ind_ate, almacen_central]
).

% Pedido 3: Granos desde Lima Norte llegando casi en simultáneo a zona_b_seco (generaría colapso de muelle con ped_002).
pedido_entrega(
    ped_003, prov_norte_pack, granos, 300, 33.0,
    440, 475, 505,
    zona_b_seco,
    [polo_norte_indep, nodo_zarumilla, nodo_linea_amarilla, nodo_javier_prado, almacen_central]
).

% Pedido 4: Insumos industriales críticos desde Lurín.
% Su ruta habitual por Javier Prado lo retrasa; por Panamericana Sur + Evitamiento cumple plazo.
pedido_entrega(
    ped_004, prov_sur_ind, insumos_industriales, 220, 44.0,
    425, 475, 505,
    zona_c_industrial,
    [centro_log_lurin, nodo_panam_sur, nodo_javier_prado, almacen_central]
).

% Pedido 5: Empaques con lote de 90 unidades cuando en almacén solo caben 50 unidades más (470/520) -> previene sobrecosto de sobrealmacenamiento.
pedido_entrega(
    ped_005, prov_agro_valle, empaques, 90, 7.2,
    455, 500, 535,
    zona_a_frio,
    [centro_log_lurin, nodo_panam_sur, nodo_javier_prado, almacen_central]
).
