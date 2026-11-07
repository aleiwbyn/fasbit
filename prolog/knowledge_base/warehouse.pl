% ==============================================================================
% FASBIT - Base de Conocimientos: Almacén y Zonas de Recepción (Muelles)
% Modela capacidades de zonas de entrega, compatibilidad de carga y stock.
% ==============================================================================

:- dynamic zona_recepcion/6.
:- dynamic inventario_producto/5.

% zona_recepcion(IdZona, Nombre, CategoriasPermitidas, CapacidadSimultaneaVehiculos, CapacidadMaxVolumenM3, TiempoDescargaMin)
zona_recepcion(
    zona_a_frio,
    'Zona A - Camaras Frigorificas',
    [refrigerado, perecibles],
    1,
    50.0,
    30
).

zona_recepcion(
    zona_b_seco,
    'Zona B - Abarrotes y Granos Secos',
    [abarrotes_secos, granos],
    1,
    85.0,
    35
).

zona_recepcion(
    zona_c_industrial,
    'Zona C - Insumos Pesados y Quimicos',
    [insumos_industriales, quimicos],
    1,
    110.0,
    40
).

zona_recepcion(
    zona_d_multiuso,
    'Zona D - Muelle Auxiliar Multiuso',
    [abarrotes_secos, granos, empaques, perecibles, insumos_industriales],
    2,
    65.0,
    35
).

% inventario_producto(Categoria, StockActualUnidades, StockMinimoSeguridad, CapacidadMaximaUnidades, VolumenUnitarioM3)
inventario_producto(refrigerado,          80,  150, 600, 0.12).   % Crítico: riesgo de quiebre de stock
inventario_producto(abarrotes_secos,     320,  250, 900, 0.10).   % Preventivo / Normal
inventario_producto(granos,              410,  300, 850, 0.11).   % Normal
inventario_producto(insumos_industriales,140,  180, 500, 0.20).   % Crítico: bajo el mínimo de seguridad
inventario_producto(empaques,            470,  150, 520, 0.08).   % Cerca del límite máximo de almacén
inventario_producto(perecibles,          110,  140, 450, 0.10).   % Crítico: bajo el mínimo de seguridad
inventario_producto(quimicos,            200,  120, 400, 0.18).   % Normal

