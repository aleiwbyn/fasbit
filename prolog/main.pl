% ==============================================================================
% FASBIT - Punto de Entrada Principal del Motor Lógico (SWI-Prolog)
% Carga de manera ordenada la Base de Conocimientos, Reglas y Puente JSON.
% ==============================================================================

:- encoding(utf8).

:- consult('knowledge_base/network.pl').
:- consult('knowledge_base/traffic.pl').
:- consult('knowledge_base/warehouse.pl').
:- consult('knowledge_base/suppliers.pl').

:- consult('rules/constraints.pl').
:- consult('rules/routing.pl').
:- consult('rules/planner.pl').

:- consult('bridge/json_api.pl').

