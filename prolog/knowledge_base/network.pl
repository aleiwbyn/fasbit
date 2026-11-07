% ==============================================================================
% FASBIT - Base de Conocimientos: Red Vial y Ubicaciones Logísticas
% Modela ubicaciones de proveedores, intersecciones viales y almacén central.
% ==============================================================================

% ubicacion(Id, Nombre, Tipo, CoordX, CoordY)
ubicacion(puerto_callao, 'Terminal Portuario del Callao', origen_proveedor, 10, 52).
ubicacion(polo_norte_indep, 'Parque Logistico Lima Norte (Independencia)', origen_proveedor, 34, 16).
ubicacion(parque_ind_ate, 'Zona Industrial Ate-Vitarte', origen_proveedor, 84, 54).
ubicacion(centro_log_lurin, 'Parque Industrial Sur (Lurin)', origen_proveedor, 56, 90).

ubicacion(nodo_faucett, 'Intercambio Vial Av. Faucett', interseccion, 22, 48).
ubicacion(nodo_zarumilla, 'Trebol Caqueta - Zarumilla', interseccion, 38, 32).
ubicacion(nodo_linea_amarilla, 'Via Expresa Linea Amarilla', interseccion, 38, 46).
ubicacion(nodo_evitamiento, 'Via de Evitamiento - Puente Nuevo', interseccion, 54, 38).
ubicacion(nodo_javier_prado, 'Eje Av. Javier Prado - Circunvalacion', interseccion, 52, 58).
ubicacion(nodo_panam_sur, 'Intercambio Atocongo - Panamericana Sur', interseccion, 56, 74).
ubicacion(nodo_ramiro_priale, 'Autopista Ramiro Priale', interseccion, 72, 34).

ubicacion(almacen_central, 'Almacen Central de Abastecimiento (Santa Anita)', destino_almacen, 68, 48).

% tramo(Origen, Destino, DistanciaKm, TiempoBaseMin, CostoBaseSoles)
% Conexiones desde Terminal Portuario del Callao
tramo(puerto_callao, nodo_faucett, 6.5, 14, 18.0).
tramo(nodo_faucett, nodo_javier_prado, 13.0, 26, 24.0).
tramo(nodo_faucett, nodo_linea_amarilla, 9.5, 13, 34.0).     % Incluye peaje pero menor tiempo base
tramo(nodo_faucett, nodo_zarumilla, 8.8, 16, 20.0).

% Conexiones desde Parque Logístico Lima Norte
tramo(polo_norte_indep, nodo_zarumilla, 7.2, 15, 17.0).
tramo(nodo_zarumilla, nodo_evitamiento, 6.8, 13, 22.0).
tramo(nodo_zarumilla, nodo_linea_amarilla, 4.5, 9, 25.0).

% Conexiones intermedias hacia Almacén Central
tramo(nodo_linea_amarilla, nodo_evitamiento, 5.2, 9, 16.0).
tramo(nodo_linea_amarilla, nodo_javier_prado, 7.8, 17, 18.0).
tramo(nodo_evitamiento, almacen_central, 7.5, 14, 19.0).
tramo(nodo_evitamiento, nodo_ramiro_priale, 8.4, 12, 18.0).
tramo(nodo_ramiro_priale, almacen_central, 5.6, 10, 14.0).
tramo(nodo_javier_prado, almacen_central, 6.4, 16, 16.0).

% Conexiones desde Parque Industrial Sur (Lurín)
tramo(centro_log_lurin, nodo_panam_sur, 16.5, 22, 32.0).
tramo(nodo_panam_sur, nodo_javier_prado, 9.2, 19, 21.0).
tramo(nodo_panam_sur, nodo_evitamiento, 12.8, 18, 28.0).

% Conexiones desde Zona Industrial Ate-Vitarte
tramo(parque_ind_ate, almacen_central, 6.8, 18, 16.0).       % Carretera Central directa (propensa a congestión)
tramo(parque_ind_ate, nodo_ramiro_priale, 6.0, 11, 15.0).    % Ruta alterna por autopista Ramiro Prialé

