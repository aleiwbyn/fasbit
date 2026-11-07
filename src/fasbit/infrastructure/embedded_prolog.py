"""
Motor lógico Prolog embebido de respaldo (Pure Python).
Lee directamente los hechos y reglas base desde los archivos `.pl` del directorio `prolog/`
cuando el usuario ejecuta el proyecto en una máquina que aún no tiene `swipl` instalado.
Garantiza portabilidad inmediata en Visual Studio Code sin instaladores `.exe` externos.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _strip_prolog_comments(source: str) -> str:
    """Elimina comentarios de línea `% ...` respetando comillas simples."""
    cleaned_lines: list[str] = []
    for line in source.splitlines():
        in_quote = False
        out_chars: list[str] = []
        for ch in line:
            if ch == "'":
                in_quote = not in_quote
                out_chars.append(ch)
            elif ch == "%" and not in_quote:
                break
            else:
                out_chars.append(ch)
        cleaned_lines.append("".join(out_chars))
    return "\n".join(cleaned_lines)


def _split_top_level(expr: str, sep: str = ",") -> list[str]:
    """Divide argumentos Prolog de nivel superior respetando listas `[...]` y comillas."""
    items: list[str] = []
    buf: list[str] = []
    depth_bracket = 0
    depth_paren = 0
    in_quote = False

    for ch in expr:
        if ch == "'":
            in_quote = not in_quote
            buf.append(ch)
        elif not in_quote:
            if ch == "[":
                depth_bracket += 1
                buf.append(ch)
            elif ch == "]":
                depth_bracket -= 1
                buf.append(ch)
            elif ch == "(":
                depth_paren += 1
                buf.append(ch)
            elif ch == ")":
                depth_paren -= 1
                buf.append(ch)
            elif ch == sep and depth_bracket == 0 and depth_paren == 0:
                items.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        else:
            buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        items.append(tail)
    return items


def _parse_prolog_term(token: str) -> Any:
    """Convierte un término atómico, numérico o lista de Prolog en valor Python."""
    t = token.strip()
    if t.startswith("'") and t.endswith("'"):
        return t[1:-1]
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_parse_prolog_term(x) for x in _split_top_level(inner)]
    try:
        if "." in t:
            return float(t)
        return int(t)
    except ValueError:
        return t


def parse_prolog_clauses(pl_path: Path) -> list[tuple[str, list[Any]]]:
    """Extrae hechos y encabezados de cláusulas desde un archivo `.pl`."""
    raw = _strip_prolog_comments(pl_path.read_text(encoding="utf-8"))
    statements = _split_top_level(raw, sep=".")
    clauses: list[tuple[str, list[Any]]] = []

    head_pattern = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*$", re.DOTALL)
    for stmt in statements:
        s = stmt.strip()
        if not s or s.startswith(":-"):
            continue
        head_part = s.split(":-")[0].strip()
        match = head_pattern.match(head_part)
        if not match:
            continue
        functor = match.group(1)
        args_raw = match.group(2)
        args = [_parse_prolog_term(a) for a in _split_top_level(args_raw)]
        clauses.append((functor, args))
    return clauses


def _round2(val: float) -> float:
    return round(val * 100.0) / 100.0


class EmbeddedPrologEngine:
    """
    Intérprete lógico embebido sincronizado con `prolog/knowledge_base/*.pl`.
    Ejecuta las mismas reglas de restricciones, DFS vial y planificación que SWI-Prolog.
    """

    def __init__(self, prolog_dir: Path) -> None:
        self._prolog_dir = prolog_dir

    def _load_kb(self, payload: dict[str, Any]) -> dict[str, Any]:
        kb_dir = self._prolog_dir / "knowledge_base"
        net_clauses = parse_prolog_clauses(kb_dir / "network.pl")
        trf_clauses = parse_prolog_clauses(kb_dir / "traffic.pl")
        wh_clauses = parse_prolog_clauses(kb_dir / "warehouse.pl")
        sup_clauses = parse_prolog_clauses(kb_dir / "suppliers.pl")

        ubicaciones = [
            {"id": a[0], "nombre": a[1], "tipo": a[2], "x": a[3], "y": a[4]}
            for f, a in net_clauses
            if f == "ubicacion"
        ]
        tramos = [
            {
                "origen": a[0],
                "destino": a[1],
                "distancia_km": float(a[2]),
                "tiempo_base_min": float(a[3]),
                "costo_base_soles": float(a[4]),
            }
            for f, a in net_clauses
            if f == "tramo"
        ]

        factor_trafico = {a[0]: float(a[1]) for f, a in trf_clauses if f == "factor_trafico"}
        factor_costo = {a[0]: float(a[1]) for f, a in trf_clauses if f == "factor_costo_trafico"}
        reglas_trafico = [a for f, a in trf_clauses if f == "trafico_base_tramo"]

        zonas = [
            {
                "id_zona": a[0],
                "nombre": a[1],
                "categorias_permitidas": list(a[2]),
                "capacidad_simultanea": int(a[3]),
                "capacidad_max_volumen_m3": float(a[4]),
                "tiempo_descarga_min": float(a[5]),
            }
            for f, a in wh_clauses
            if f == "zona_recepcion"
        ]

        inventario: dict[str, dict[str, Any]] = {}
        for f, a in wh_clauses:
            if f == "inventario_producto":
                inventario[a[0]] = {
                    "categoria": a[0],
                    "stock_actual": int(a[1]),
                    "stock_minimo": int(a[2]),
                    "capacidad_maxima": int(a[3]),
                    "volumen_unitario_m3": float(a[4]),
                }

        for ov in payload.get("stock_overrides") or []:
            cat = ov["categoria"]
            if cat in inventario:
                if "stock_actual" in ov:
                    inventario[cat]["stock_actual"] = int(ov["stock_actual"])
                if "stock_minimo" in ov:
                    inventario[cat]["stock_minimo"] = int(ov["stock_minimo"])
                if "capacidad_maxima" in ov:
                    inventario[cat]["capacidad_maxima"] = int(ov["capacidad_maxima"])

        proveedores = {
            a[0]: {
                "id_proveedor": a[0],
                "nombre": a[1],
                "origen": a[2],
                "multa_soles_por_min": float(a[3]),
            }
            for f, a in sup_clauses
            if f == "proveedor"
        }

        custom_orders = payload.get("custom_orders") or []
        if custom_orders:
            pedidos = [
                {
                    "id_pedido": str(p["id_pedido"]),
                    "id_proveedor": str(p["id_proveedor"]),
                    "categoria": str(p["categoria"]),
                    "cantidad": int(p["cantidad"]),
                    "volumen_m3": float(p["volumen_m3"]),
                    "hora_salida_min": float(p["hora_salida_min"]),
                    "ventana_inicio_min": float(p["ventana_inicio_min"]),
                    "plazo_maximo_min": float(p["plazo_maximo_min"]),
                    "zona_habitual": str(p["zona_habitual"]),
                    "ruta_habitual": list(p["ruta_habitual"]),
                }
                for p in custom_orders
            ]
        else:
            pedidos = [
                {
                    "id_pedido": a[0],
                    "id_proveedor": a[1],
                    "categoria": a[2],
                    "cantidad": int(a[3]),
                    "volumen_m3": float(a[4]),
                    "hora_salida_min": float(a[5]),
                    "ventana_inicio_min": float(a[6]),
                    "plazo_maximo_min": float(a[7]),
                    "zona_habitual": a[8],
                    "ruta_habitual": list(a[9]),
                }
                for f, a in sup_clauses
                if f == "pedido_entrega"
            ]

        traffic_overrides = {
            (t["origen"], t["destino"]): t["nivel"]
            for t in (payload.get("traffic_overrides") or [])
        }

        return {
            "ubicaciones": ubicaciones,
            "tramos": tramos,
            "factor_trafico": factor_trafico,
            "factor_costo": factor_costo,
            "reglas_trafico": reglas_trafico,
            "traffic_overrides": traffic_overrides,
            "zonas": zonas,
            "inventario": inventario,
            "proveedores": proveedores,
            "pedidos": pedidos,
        }

    @staticmethod
    def _criticidad_stock(stock_actual: int, stock_minimo: int) -> tuple[str, int]:
        if stock_actual < stock_minimo:
            return "critico_riesgo_quiebre", 1
        if stock_actual < stock_minimo * 1.30:
            return "alerta_preventiva", 2
        return "stock_saludable", 3

    @staticmethod
    def _franja_horaria(minuto_dia: float) -> str:
        m = int(round(minuto_dia)) % 1440
        if 390 <= m <= 570:
            return "hora_punta_manana"
        if 570 < m <= 990:
            return "valle_diurno"
        if 990 < m <= 1230:
            return "hora_punta_tarde"
        return "nocturno"

    def _nivel_trafico(self, kb: dict[str, Any], origen: str, destino: str, hora_min: float) -> str:
        override = kb["traffic_overrides"].get((origen, destino))
        if override:
            return override
        franja = self._franja_horaria(hora_min)
        for o_pat, d_pat, f_pat, nivel in kb["reglas_trafico"]:
            o_ok = o_pat == "_" or o_pat == origen
            d_ok = d_pat == "_" or d_pat == destino
            f_ok = f_pat == "_" or f_pat == franja
            if o_ok and d_ok and f_ok:
                return str(nivel)
        return "bajo"

    def _eval_tramo(self, kb: dict[str, Any], tr: dict[str, Any], hora_min: float) -> dict[str, Any]:
        nivel = self._nivel_trafico(kb, tr["origen"], tr["destino"], hora_min)
        ft = kb["factor_trafico"][nivel]
        fc = kb["factor_costo"][nivel]
        t_real = _round2(tr["tiempo_base_min"] * ft)
        c_real = _round2(tr["costo_base_soles"] * fc)
        return {
            "origen": tr["origen"],
            "destino": tr["destino"],
            "distancia_km": tr["distancia_km"],
            "tiempo_base_min": tr["tiempo_base_min"],
            "tiempo_real_min": t_real,
            "costo_soles": c_real,
            "trafico": nivel,
        }

    def _dfs_rutas(
        self,
        kb: dict[str, Any],
        actual: str,
        destino: str,
        hora_actual: float,
        visitados: list[str],
    ) -> list[tuple[list[str], list[dict[str, Any]], float, float, float]]:
        if actual == destino:
            return [([destino], [], 0.0, 0.0, 0.0)]
        resultados = []
        for tr in kb["tramos"]:
            if tr["origen"] != actual or tr["destino"] in visitados:
                continue
            step = self._eval_tramo(kb, tr, hora_actual)
            sub_rutas = self._dfs_rutas(
                kb,
                tr["destino"],
                destino,
                hora_actual + step["tiempo_real_min"],
                visitados + [tr["destino"]],
            )
            for nodos_r, tramos_r, d_r, t_r, c_r in sub_rutas:
                resultados.append(
                    (
                        [actual] + nodos_r,
                        [step] + tramos_r,
                        d_r + step["distancia_km"],
                        t_r + step["tiempo_real_min"],
                        c_r + step["costo_soles"],
                    )
                )
        return resultados

    @staticmethod
    def _eval_plazo(
        llegada: float, ventana_ini: float, plazo_max: float, multa_min: float
    ) -> tuple[str, float, float, float]:
        if llegada <= plazo_max:
            return "a_tiempo", 0.0, _round2(max(0.0, ventana_ini - llegada)), 0.0
        retraso = _round2(llegada - plazo_max)
        multa = _round2(retraso * multa_min)
        return "retrasado", retraso, 0.0, multa

    def _rutas_ordenadas(
        self,
        kb: dict[str, Any],
        origen: str,
        destino: str,
        hora_salida: float,
        ventana_ini: float,
        plazo_max: float,
        multa_min: float,
    ) -> list[dict[str, Any]]:
        caminos = self._dfs_rutas(kb, origen, destino, hora_salida, [origen])
        pares: list[tuple[float, dict[str, Any]]] = []
        for nodos, tramos, dist_raw, t_raw, c_raw in caminos:
            dist = _round2(dist_raw)
            tiempo = _round2(t_raw)
            costo_tr = _round2(c_raw)
            llegada = _round2(hora_salida + tiempo)
            estado, retraso, espera, multa = self._eval_plazo(llegada, ventana_ini, plazo_max, multa_min)
            costo_total = _round2(costo_tr + multa)
            penal_sla = 60.0 if estado == "retrasado" else 0.0
            puntaje = _round2(costo_tr + multa + penal_sla + (tiempo * 0.35))
            pares.append(
                (
                    puntaje,
                    {
                        "nodos": nodos,
                        "tramos": tramos,
                        "distancia_km": dist,
                        "tiempo_transito_min": tiempo,
                        "hora_salida_min": hora_salida,
                        "hora_llegada_min": llegada,
                        "estado_puntualidad": estado,
                        "minutos_retraso": retraso,
                        "minutos_espera_ventana": espera,
                        "costo_transporte_soles": costo_tr,
                        "costo_multa_soles": multa,
                        "costo_total_ruta_soles": costo_total,
                        "puntaje_optimizacion": puntaje,
                    },
                )
            )
        pares.sort(key=lambda x: x[0])
        return [p[1] for p in pares]

    def _eval_ruta_fija(
        self, kb: dict[str, Any], nodos: list[str], hora_salida: float
    ) -> tuple[list[dict[str, Any]], float, float, float]:
        tramos_idx = {(t["origen"], t["destino"]): t for t in kb["tramos"]}
        tramos_out = []
        hora = hora_salida
        dist = 0.0
        tiempo = 0.0
        costo = 0.0
        for i in range(len(nodos) - 1):
            tr = tramos_idx[(nodos[i], nodos[i + 1])]
            step = self._eval_tramo(kb, tr, hora)
            tramos_out.append(step)
            hora += step["tiempo_real_min"]
            dist += step["distancia_km"]
            tiempo += step["tiempo_real_min"]
            costo += step["costo_soles"]
        return tramos_out, _round2(dist), _round2(tiempo), _round2(costo)

    @staticmethod
    def _zona_valida(z: dict[str, Any], categoria: str, volumen: float) -> bool:
        return categoria in z["categorias_permitidas"] and volumen <= z["capacidad_max_volumen_m3"]

    @staticmethod
    def _ocupados_en_ventana(
        id_zona: str, inicio: float, fin: float, reservas: list[tuple[str, float, float, str]]
    ) -> int:
        return sum(
            1
            for rz, ri, rf, _ in reservas
            if rz == id_zona and inicio < rf and ri < fin
        )

    def _asignar_zona(
        self,
        kb: dict[str, Any],
        categoria: str,
        volumen: float,
        hora_disp: float,
        zona_hab: str,
        reservas: list[tuple[str, float, float, str]],
    ) -> tuple[str, str, float, float, float, str]:
        zonas_by_id = {z["id_zona"]: z for z in kb["zonas"]}
        hab_valida = zona_hab in zonas_by_id and self._zona_valida(zonas_by_id[zona_hab], categoria, volumen)

        candidatos_inm = []
        for z in kb["zonas"]:
            if not self._zona_valida(z, categoria, volumen):
                continue
            ini = hora_disp
            fin = _round2(ini + z["tiempo_descarga_min"])
            if self._ocupados_en_ventana(z["id_zona"], ini, fin, reservas) < z["capacidad_simultanea"]:
                pref = 0 if z["id_zona"] == zona_hab else (2 if z["id_zona"] == "zona_d_multiuso" else 1)
                candidatos_inm.append((pref, z["id_zona"], z["nombre"], ini, fin))

        if candidatos_inm:
            candidatos_inm.sort(key=lambda x: x[0])
            _, id_z, nom_z, ini, fin = candidatos_inm[0]
            espera = 0.0
        else:
            diferidos = []
            for z in kb["zonas"]:
                if not self._zona_valida(z, categoria, volumen):
                    continue
                puntos = sorted(
                    {hora_disp}
                    | {rf for rz, _, rf, _ in reservas if rz == z["id_zona"] and rf > hora_disp}
                )
                for p in puntos:
                    ini = _round2(p)
                    fin = _round2(ini + z["tiempo_descarga_min"])
                    if self._ocupados_en_ventana(z["id_zona"], ini, fin, reservas) < z["capacidad_simultanea"]:
                        diferidos.append((ini, z["id_zona"], z["nombre"], ini, fin))
                        break
            diferidos.sort(key=lambda x: x[0])
            _, id_z, nom_z, ini, fin = diferidos[0]
            espera = _round2(ini - hora_disp)

        if not hab_valida:
            accion = "corregida_zona_incompatible"
        elif zona_hab != id_z:
            accion = "reasignada_evitar_colapso"
        elif espera > 0:
            accion = "turno_escalonado_sin_colapso"
        else:
            accion = "zona_confirmada_optima"

        return id_z, nom_z, ini, fin, espera, accion

    def _planificar(self, kb: dict[str, Any]) -> list[dict[str, Any]]:
        pedidos_ordenados = sorted(
            kb["pedidos"],
            key=lambda p: (
                self._criticidad_stock(
                    kb["inventario"][p["categoria"]]["stock_actual"],
                    kb["inventario"][p["categoria"]]["stock_minimo"],
                )[1],
                p["plazo_maximo_min"],
                p["id_pedido"],
            ),
        )

        reservas: list[tuple[str, float, float, str]] = []
        stocks = {cat: info["stock_actual"] for cat, info in kb["inventario"].items()}
        tareas = []

        for p in pedidos_ordenados:
            prov = kb["proveedores"][p["id_proveedor"]]
            inv = kb["inventario"][p["categoria"]]
            stock_antes = stocks[p["categoria"]]
            estado_stock, prio = self._criticidad_stock(stock_antes, inv["stock_minimo"])

            espacio = max(0, inv["capacidad_maxima"] - stock_antes)
            if p["cantidad"] <= espacio:
                decision = "recepcion_completa"
                aceptada = p["cantidad"]
                exceso = 0
            elif espacio > 0:
                decision = "recepcion_parcial_tope_almacen"
                aceptada = espacio
                exceso = p["cantidad"] - espacio
            else:
                decision = "rechazado_almacen_lleno"
                aceptada = 0
                exceso = p["cantidad"]

            rutas = self._rutas_ordenadas(
                kb,
                prov["origen"],
                "almacen_central",
                p["hora_salida_min"],
                p["ventana_inicio_min"],
                p["plazo_maximo_min"],
                prov["multa_soles_por_min"],
            )
            mejor = rutas[0]
            hora_lista = _round2(max(mejor["hora_llegada_min"], p["ventana_inicio_min"]))

            if aceptada > 0:
                vol_ef = _round2(p["volumen_m3"] * (aceptada / p["cantidad"]))
                z_id, z_nom, ini_d, fin_d, esp_m, acc_z = self._asignar_zona(
                    kb, p["categoria"], vol_ef, hora_lista, p["zona_habitual"], reservas
                )
                reservas.append((z_id, ini_d, fin_d, p["id_pedido"]))
            else:
                vol_ef = 0.0
                z_id = "sin_descarga"
                z_nom = "Sin descarga (Almacen al limite)"
                ini_d = hora_lista
                fin_d = hora_lista
                esp_m = 0.0
                acc_z = "descarga_omitida_tope_stock"

            stock_despues = stock_antes + aceptada
            stocks[p["categoria"]] = stock_despues

            tareas.append(
                {
                    "id_pedido": p["id_pedido"],
                    "id_proveedor": p["id_proveedor"],
                    "nombre_proveedor": prov["nombre"],
                    "origen": prov["origen"],
                    "categoria": p["categoria"],
                    "prioridad_stock": prio,
                    "estado_stock_previo": estado_stock,
                    "stock_antes": stock_antes,
                    "stock_despues": stock_despues,
                    "cantidad_solicitada": p["cantidad"],
                    "cantidad_aceptada": aceptada,
                    "unidades_exceso_evitadas": exceso,
                    "decision_almacen": decision,
                    "volumen_efectivo_m3": vol_ef,
                    "ventana_inicio_min": p["ventana_inicio_min"],
                    "plazo_maximo_min": p["plazo_maximo_min"],
                    "zona_habitual_proveedor": p["zona_habitual"],
                    "zona_asignada": z_id,
                    "nombre_zona_asignada": z_nom,
                    "accion_zona": acc_z,
                    "inicio_descarga_min": ini_d,
                    "fin_descarga_min": fin_d,
                    "espera_muelle_min": esp_m,
                    "rutas_evaluadas": len(rutas),
                    "ruta": mejor,
                    "costo_sobrealmacenamiento_soles": 0.0,
                    "costo_operativo_total_soles": mejor["costo_total_ruta_soles"],
                }
            )
        return tareas

    def _simular_base(self, kb: dict[str, Any]) -> list[dict[str, Any]]:
        zonas_by_id = {z["id_zona"]: z for z in kb["zonas"]}
        ocupacion: list[tuple[str, float, float, str]] = []
        stocks = {cat: info["stock_actual"] for cat, info in kb["inventario"].items()}
        resultados = []

        for p in kb["pedidos"]:
            prov = kb["proveedores"][p["id_proveedor"]]
            tramos, dist, tiempo, costo_tr = self._eval_ruta_fija(kb, p["ruta_habitual"], p["hora_salida_min"])
            llegada = _round2(p["hora_salida_min"] + tiempo)
            estado, retraso, espera, multa = self._eval_plazo(
                llegada, p["ventana_inicio_min"], p["plazo_maximo_min"], prov["multa_soles_por_min"]
            )
            zona = zonas_by_id[p["zona_habitual"]]
            ini_int = max(llegada, p["ventana_inicio_min"])
            fin_int = ini_int + zona["tiempo_descarga_min"]

            if self._zona_valida(zona, p["categoria"], p["volumen_m3"]):
                err_pos = False
                costo_rep = 0.0
            else:
                err_pos = True
                costo_rep = 45.0

            solapados = self._ocupados_en_ventana(p["zona_habitual"], ini_int, fin_int, ocupacion)
            if solapados >= zona["capacidad_simultanea"]:
                colapso = True
                costo_cong = 35.0
            else:
                colapso = False
                costo_cong = 0.0

            inv = kb["inventario"][p["categoria"]]
            stock_antes = stocks[p["categoria"]]
            espacio = max(0, inv["capacidad_maxima"] - stock_antes)
            exceso = max(0, p["cantidad"] - espacio)
            costo_sobre = _round2(exceso * 1.85)
            stocks[p["categoria"]] = min(inv["capacidad_maxima"], stock_antes + p["cantidad"])

            costo_total = _round2(costo_tr + multa + costo_rep + costo_cong + costo_sobre)
            ocupacion.append((p["zona_habitual"], ini_int, fin_int, p["id_pedido"]))

            resultados.append(
                {
                    "id_pedido": p["id_pedido"],
                    "id_proveedor": p["id_proveedor"],
                    "nombre_proveedor": prov["nombre"],
                    "origen": prov["origen"],
                    "categoria": p["categoria"],
                    "cantidad_solicitada": p["cantidad"],
                    "unidades_exceso_almacen": exceso,
                    "ventana_inicio_min": p["ventana_inicio_min"],
                    "plazo_maximo_min": p["plazo_maximo_min"],
                    "zona_intentada": p["zona_habitual"],
                    "nombre_zona_intentada": zona["nombre"],
                    "error_posicionamiento_zona": err_pos,
                    "colapso_zona_recepcion": colapso,
                    "inicio_recepcion_min": ini_int,
                    "fin_recepcion_min": fin_int,
                    "ruta": {
                        "nodos": p["ruta_habitual"],
                        "tramos": tramos,
                        "distancia_km": dist,
                        "tiempo_transito_min": tiempo,
                        "hora_salida_min": p["hora_salida_min"],
                        "hora_llegada_min": llegada,
                        "estado_puntualidad": estado,
                        "minutos_retraso": retraso,
                        "minutos_espera_ventana": espera,
                        "costo_transporte_soles": costo_tr,
                        "costo_multa_soles": multa,
                        "costo_total_ruta_soles": costo_total,
                    },
                    "costo_reproceso_zona_soles": costo_rep,
                    "costo_congestion_muelle_soles": costo_cong,
                    "costo_sobrealmacenamiento_soles": costo_sobre,
                    "costo_operativo_total_soles": costo_total,
                }
            )
        return resultados

    def query(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action")
        if action == "health":
            return {"status": "ok", "engine": "prolog_embedded_kb", "modules_loaded": True}

        kb = self._load_kb(payload)

        if action == "inspect_state":
            inv_out = []
            for item in kb["inventario"].values():
                est, _ = self._criticidad_stock(item["stock_actual"], item["stock_minimo"])
                inv_out.append({**item, "estado_criticidad": est})
            return {
                "status": "ok",
                "ubicaciones": kb["ubicaciones"],
                "tramos": kb["tramos"],
                "zonas_recepcion": kb["zonas"],
                "inventario": inv_out,
                "proveedores": list(kb["proveedores"].values()),
                "pedidos": kb["pedidos"],
            }

        if action == "find_routes":
            rutas = self._rutas_ordenadas(
                kb,
                str(payload["origen"]),
                str(payload["destino"]),
                float(payload["hora_salida_min"]),
                float(payload["ventana_inicio_min"]),
                float(payload["plazo_maximo_min"]),
                float(payload["multa_por_minuto"]),
            )
            return {
                "status": "ok",
                "total_alternativas": len(rutas),
                "ruta_optima": rutas[0] if rutas else None,
                "alternativas": rutas,
            }

        if action == "plan_tasks":
            return {"status": "ok", "tareas_planificadas": self._planificar(kb)}

        if action == "compare_simulation":
            return {
                "status": "ok",
                "escenario_base": self._simular_base(kb),
                "escenario_optimizado": self._planificar(kb),
            }

        return {"status": "error", "message": f"Acción no reconocida: {action}"}

