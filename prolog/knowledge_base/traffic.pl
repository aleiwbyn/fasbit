% ==============================================================================
% FASBIT - Base de Conocimientos: Tráfico y Factores de Congestión
% Modela el impacto del tráfico por horario y overrides dinámicos de simulación.
% ==============================================================================

:- dynamic trafico_override/3.
:- dynamic factor_global_trafico/1.

% Multiplicadores de tiempo según nivel de tráfico
factor_trafico(bajo, 1.00).
factor_trafico(moderado, 1.28).
factor_trafico(alto, 1.70).
factor_trafico(critico, 2.35).

% Multiplicadores de costo operativo (mayor consumo de combustible en congestión)
factor_costo_trafico(bajo, 1.00).
factor_costo_trafico(moderado, 1.08).
factor_costo_trafico(alto, 1.22).
factor_costo_trafico(critico, 1.42).

% Clasificación de franjas horarias (minutos desde las 00:00)
% 06:30 (390) a 09:30 (570) -> hora_punta_manana
% 09:31 (571) a 16:30 (990) -> valle_diurno
% 16:31 (991) a 20:30 (1230) -> hora_punta_tarde
% Resto -> nocturno
franja_horaria(MinutoDia, hora_punta_manana) :-
    MinutoDia >= 390, MinutoDia =< 570, !.
franja_horaria(MinutoDia, valle_diurno) :-
    MinutoDia > 570, MinutoDia =< 990, !.
franja_horaria(MinutoDia, hora_punta_tarde) :-
    MinutoDia > 990, MinutoDia =< 1230, !.
franja_horaria(_, nocturno).

% Nivel de tráfico habitual por tramo y franja horaria
% Ejes arteriales críticos en hora punta (Javier Prado, Carretera Central, Faucett)
trafico_base_tramo(nodo_faucett, nodo_javier_prado, hora_punta_manana, critico) :- !.
trafico_base_tramo(nodo_javier_prado, almacen_central, hora_punta_manana, critico) :- !.
trafico_base_tramo(parque_ind_ate, almacen_central, hora_punta_manana, critico) :- !.
trafico_base_tramo(nodo_panam_sur, nodo_javier_prado, hora_punta_manana, alto) :- !.
trafico_base_tramo(puerto_callao, nodo_faucett, hora_punta_manana, alto) :- !.
trafico_base_tramo(polo_norte_indep, nodo_zarumilla, hora_punta_manana, alto) :- !.
trafico_base_tramo(nodo_zarumilla, nodo_evitamiento, hora_punta_manana, moderado) :- !.
trafico_base_tramo(nodo_evitamiento, almacen_central, hora_punta_manana, moderado) :- !.
trafico_base_tramo(nodo_faucett, nodo_linea_amarilla, hora_punta_manana, bajo) :- !.
trafico_base_tramo(nodo_linea_amarilla, nodo_evitamiento, hora_punta_manana, bajo) :- !.
trafico_base_tramo(nodo_ramiro_priale, almacen_central, hora_punta_manana, bajo) :- !.
trafico_base_tramo(parque_ind_ate, nodo_ramiro_priale, hora_punta_manana, bajo) :- !.
trafico_base_tramo(_, _, hora_punta_manana, moderado) :- !.

% Hora punta tarde
trafico_base_tramo(nodo_faucett, nodo_javier_prado, hora_punta_tarde, critico) :- !.
trafico_base_tramo(nodo_javier_prado, almacen_central, hora_punta_tarde, alto) :- !.
trafico_base_tramo(parque_ind_ate, almacen_central, hora_punta_tarde, critico) :- !.
trafico_base_tramo(nodo_evitamiento, almacen_central, hora_punta_tarde, alto) :- !.
trafico_base_tramo(_, _, hora_punta_tarde, moderado) :- !.

% Valle diurno
trafico_base_tramo(nodo_faucett, nodo_javier_prado, valle_diurno, moderado) :- !.
trafico_base_tramo(parque_ind_ate, almacen_central, valle_diurno, alto) :- !.
trafico_base_tramo(_, _, valle_diurno, bajo) :- !.

% Nocturno
trafico_base_tramo(_, _, nocturno, bajo).

% Determinación efectiva del tráfico en un tramo (prioriza overrides de simulación)
nivel_trafico_efectivo(Origen, Destino, _, Nivel) :-
    trafico_override(Origen, Destino, Nivel), !.
nivel_trafico_efectivo(Origen, Destino, MinutoActual, Nivel) :-
    MinutoEntero is round(MinutoActual),
    MinutoNorm is MinutoEntero mod 1440,
    franja_horaria(MinutoNorm, Franja),
    trafico_base_tramo(Origen, Destino, Franja, Nivel).
