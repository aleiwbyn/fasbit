/**
 * FASBIT — Interfaz Minimalista de Despacho y Planificación Lógica
 * Sincroniza esquema vial SVG, inspector causal Prolog, Gantt de muelles,
 * balance de inventario y laboratorio interactivo de inferencia.
 */

const NODE_LABELS = {
  puerto_callao: "Puerto Callao",
  polo_norte_indep: "Lima Norte",
  parque_ind_ate: "Ate-Vitarte",
  centro_log_lurin: "Sur · Lurín",
  nodo_faucett: "Av. Faucett",
  nodo_zarumilla: "Zarumilla",
  nodo_linea_amarilla: "Línea Amarilla",
  nodo_evitamiento: "Evitamiento",
  nodo_javier_prado: "Javier Prado",
  nodo_panam_sur: "Panam. Sur",
  nodo_ramiro_priale: "Ramiro Prialé",
  almacen_central: "Almacén Santa Anita",
};

const CATEGORY_LABELS = {
  refrigerado: "Refrigerados",
  abarrotes_secos: "Abarrotes secos",
  granos: "Granos y cereales",
  insumos_industriales: "Insumos industriales",
  empaques: "Empaques",
  perecibles: "Perecibles frescos",
  quimicos: "Químicos",
};

const ZONE_SHORT = {
  zona_a_frio: "Muelle A · Frío",
  zona_b_seco: "Muelle B · Secos",
  zona_c_industrial: "Muelle C · Industrial",
  zona_d_multiuso: "Muelle D · Auxiliar",
  sin_descarga: "Sin descarga",
};

const ZONE_ACTION_COPY = {
  zona_confirmada_optima: {
    badge: "Muelle confirmado",
    tone: "clear",
    detail: "Compatible con la categoría de carga y libre en la ventana de llegada.",
  },
  corregida_zona_incompatible: {
    badge: "Zona corregida",
    tone: "caution",
    detail: "El muelle habitual solicitado por el proveedor no admite este tipo de producto.",
  },
  reasignada_evitar_colapso: {
    badge: "Desvío anti-colapso",
    tone: "logic",
    detail: "Muelle principal ocupado en ese horario; reasignado a muelle auxiliar compatible.",
  },
  turno_escalonado_sin_colapso: {
    badge: "Turno escalonado",
    tone: "logic",
    detail: "Programado en el primer turno libre para respetar la capacidad simultánea.",
  },
  descarga_omitida_tope_stock: {
    badge: "Almacén lleno",
    tone: "breach",
    detail: "Descarga omitida porque el almacén alcanzó su tope máximo.",
  },
};

const STOCK_DECISION_COPY = {
  recepcion_completa: "Recepción íntegra autorizada dentro de capacidad.",
  recepcion_parcial_tope_almacen: "Ajustada automáticamente al espacio disponible para evitar sobrecosto.",
  rechazado_almacen_lleno: "Bloqueada: capacidad física agotada en almacén.",
};

const GANTT_START_MIN = 410; // 06:50
const GANTT_END_MIN = 590;   // 09:50

const state = {
  snapshot: null,
  scenarios: [],
  currentSim: null,
  selectedOrderId: null,
  activeView: "dispatch",
  mapMode: "compare",      // "compare" | "optimal"
  ganttMode: "optimized",  // "optimized" | "baseline"
};

/* ==========================================================================
   Utilidades Puras
   ========================================================================== */

function humanNode(id) {
  return NODE_LABELS[id] || id;
}

function humanCategory(cat) {
  return CATEGORY_LABELS[cat] || cat;
}

function humanZone(id) {
  return ZONE_SHORT[id] || id;
}

function hhmmToMinutes(hhmm) {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

function minutesToHhmm(mins) {
  const rounded = Math.round(mins);
  const h = Math.floor(rounded / 60) % 24;
  const m = rounded % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function formatSoles(amount) {
  return `S/ ${Number(amount).toFixed(2)}`;
}

function buildEdgeSet(nodos) {
  const set = new Set();
  for (let i = 0; i < nodos.length - 1; i += 1) {
    set.add(`${nodos[i]}->${nodos[i + 1]}`);
  }
  return set;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Error de comunicación con el servidor");
  }
  return res.json();
}

/* ==========================================================================
   Navegación y Controles Superiores
   ========================================================================== */

function switchView(viewName) {
  state.activeView = viewName;
  const tabs = document.querySelectorAll(".segmented-nav__btn");
  tabs.forEach((btn) => {
    const active = btn.dataset.view === viewName;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-selected", String(active));
  });

  document.querySelectorAll(".view-panel").forEach((panel) => {
    const isTarget = panel.id === `panel-${viewName}`;
    panel.hidden = !isTarget;
    panel.classList.toggle("is-active", isTarget);
  });
}

function bindNavigation() {
  const tabs = Array.from(document.querySelectorAll(".segmented-nav__btn"));
  tabs.forEach((btn, idx) => {
    btn.addEventListener("click", () => switchView(btn.dataset.view));
    btn.addEventListener("keydown", (ev) => {
      let nextIdx = null;
      if (ev.key === "ArrowRight") nextIdx = (idx + 1) % tabs.length;
      if (ev.key === "ArrowLeft") nextIdx = (idx - 1 + tabs.length) % tabs.length;
      if (ev.key === "Home") nextIdx = 0;
      if (ev.key === "End") nextIdx = tabs.length - 1;
      if (nextIdx !== null) {
        ev.preventDefault();
        tabs[nextIdx].focus();
        switchView(tabs[nextIdx].dataset.view);
      }
    });
  });

  document.querySelectorAll("[data-mapmode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.mapMode = btn.dataset.mapmode;
      document.querySelectorAll("[data-mapmode]").forEach((b) => {
        b.classList.toggle("is-active", b.dataset.mapmode === state.mapMode);
      });
      renderSchematicMap();
    });
  });

  document.querySelectorAll("[data-ganttmode]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.ganttMode = btn.dataset.ganttmode;
      document.querySelectorAll("[data-ganttmode]").forEach((b) => {
        b.classList.toggle("is-active", b.dataset.ganttmode === state.ganttMode);
      });
      renderDockGantt();
    });
  });
}

function selectOrder(orderId) {
  if (!state.currentSim || !orderId) return;
  state.selectedOrderId = orderId;
  renderSchematicMap();
  renderOrderInspector();
  renderDockGantt();
  renderManifestTable();
}

/* ==========================================================================
   Encabezado Contextual y Franja de Telemetría
   ========================================================================== */

function renderHeaderAndTelemetry() {
  const sim = state.currentSim;
  if (!sim) return;

  const esc = sim.escenario;
  const b = sim.kpis_base;
  const o = sim.kpis_optimizado;
  const imp = sim.impacto;

  const cleanTitle = esc.nombre.replace(/^Escenario\s+\d+:\s*/i, "");
  document.getElementById("scenarioEyebrow").textContent = `ESCENARIO ACTIVO · ${esc.id.replace(/_/g, " ").toUpperCase()}`;
  document.getElementById("scenarioTitle").textContent = cleanTitle;
  document.getElementById("scenarioDesc").textContent = esc.descripcion;

  const badges = [];
  badges.push(`<span class="pill pill--neutral">${o.total_pedidos} órdenes evaluadas</span>`);
  if (esc.traffic_overrides && esc.traffic_overrides.length > 0) {
    badges.push(`<span class="pill pill--caution">${esc.traffic_overrides.length} contingencias viales</span>`);
  }
  if (imp.alertas_quiebre_priorizadas > 0) {
    badges.push(`<span class="pill pill--breach">${imp.alertas_quiebre_priorizadas} alertas P1 de quiebre</span>`);
  }
  document.getElementById("scenarioBadges").innerHTML = badges.join("");

  const totalMitigated = imp.errores_zona_mitigados + imp.colapsos_muelle_evitados + (imp.unidades_exceso_bloqueadas > 0 ? 1 : 0);

  document.getElementById("telemetryStrip").innerHTML = `
    <div class="telemetry-cell">
      <span class="telemetry-label">Puntualidad SLA</span>
      <div class="telemetry-hero-row">
        <span class="telemetry-value">${o.tasa_puntualidad_pct.toFixed(0)}%</span>
        <span class="pill pill--clear">+${imp.mejora_puntualidad_pp.toFixed(0)} pp</span>
      </div>
      <span class="telemetry-meta">${o.entregas_a_tiempo}/${o.total_pedidos} a tiempo · Habitual ${b.tasa_puntualidad_pct.toFixed(0)}% (${b.entregas_a_tiempo}/${b.total_pedidos})</span>
    </div>

    <div class="telemetry-cell">
      <span class="telemetry-label">Costo Operativo Total</span>
      <div class="telemetry-hero-row">
        <span class="telemetry-value">${formatSoles(o.costo_total_soles)}</span>
        <span class="pill pill--clear">−${imp.reduccion_costo_pct.toFixed(1)}%</span>
      </div>
      <span class="telemetry-meta">Ahorro neto ${formatSoles(imp.ahorro_total_soles)} frente a ${formatSoles(b.costo_total_soles)}</span>
    </div>

    <div class="telemetry-cell">
      <span class="telemetry-label">Retraso Acumulado</span>
      <div class="telemetry-hero-row">
        <span class="telemetry-value">${o.minutos_retraso_total.toFixed(1)} min</span>
        <span class="pill pill--neutral">−${imp.reduccion_retrasos_min.toFixed(1)} min</span>
      </div>
      <span class="telemetry-meta">Multas ${formatSoles(b.costo_multas_soles)} → ${formatSoles(o.costo_multas_soles)}</span>
    </div>

    <div class="telemetry-cell">
      <span class="telemetry-label">Riesgos Mitigados</span>
      <div class="telemetry-hero-row">
        <span class="telemetry-value">${totalMitigated}</span>
        <span class="pill pill--logic">0 colapsos</span>
      </div>
      <span class="telemetry-meta">${imp.errores_zona_mitigados} zonas corregidas · ${imp.colapsos_muelle_evitados} colapsos · ${imp.unidades_exceso_bloqueadas} uds tope</span>
    </div>
  `;
}

/* ==========================================================================
   Esquema Vial Minimalista (SVG)
   ========================================================================== */

function renderSchematicMap() {
  const svg = document.getElementById("networkSvg");
  if (!state.snapshot || !state.currentSim) return;

  const nodesById = {};
  state.snapshot.ubicaciones.forEach((u) => {
    nodesById[u.id] = {
      ...u,
      px: 56 + u.x * 8.1,
      py: 26 + u.y * 4.05,
    };
  });

  const optTask = state.currentSim.tareas_optimizadas.find((t) => t.id_pedido === state.selectedOrderId);
  const baseTask = state.currentSim.tareas_base.find((t) => t.id_pedido === state.selectedOrderId);

  const optEdges = optTask ? buildEdgeSet(optTask.ruta.nodos) : new Set();
  const baseEdges = baseTask && state.mapMode === "compare" ? buildEdgeSet(baseTask.ruta.nodos) : new Set();
  const activeNodes = new Set([
    ...(optTask ? optTask.ruta.nodos : []),
    ...(baseTask && state.mapMode === "compare" ? baseTask.ruta.nodos : []),
  ]);

  // Mapa rápido de orden por nodo de origen para selección directa en clic
  const orderByOrigin = {};
  state.currentSim.tareas_optimizadas.forEach((t) => {
    if (!orderByOrigin[t.origen]) orderByOrigin[t.origen] = t.id_pedido;
  });

  let defs = `
    <defs>
      <marker id="arrowOpt" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#0B7A5C" />
      </marker>
      <marker id="arrowBase" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#BE123C" />
      </marker>
    </defs>
  `;

  let baseLines = "";
  let highlightLines = "";

  state.snapshot.tramos.forEach((tr) => {
    const a = nodesById[tr.origen];
    const b = nodesById[tr.destino];
    if (!a || !b) return;

    const key = `${tr.origen}->${tr.destino}`;
    const isOpt = optEdges.has(key);
    const isBase = baseEdges.has(key);

    // Línea estructural de fondo
    baseLines += `<line x1="${a.px}" y1="${a.py}" x2="${b.px}" y2="${b.py}" stroke="rgba(20,21,24,0.11)" stroke-width="1.75" stroke-linecap="round" />`;

    if (isBase && !isOpt) {
      highlightLines += `<line x1="${a.px}" y1="${a.py}" x2="${b.px}" y2="${b.py}" stroke="#BE123C" stroke-width="2.6" stroke-dasharray="6 5" marker-end="url(#arrowBase)" opacity="0.85" />`;
    }
    if (isOpt) {
      highlightLines += `<line x1="${a.px}" y1="${a.py}" x2="${b.px}" y2="${b.py}" stroke="#0B7A5C" stroke-width="3.6" stroke-linecap="round" marker-end="url(#arrowOpt)" />`;
    }
  });

  let nodesMarkup = "";
  Object.values(nodesById).forEach((n) => {
    const isSelectedOrigin = optTask && optTask.origen === n.id;
    const isVisited = activeNodes.has(n.id);

    let fill = "#FFFFFF";
    let stroke = "#8A8F98";
    let radius = 5.5;

    if (n.tipo === "origen_proveedor") {
      fill = isSelectedOrigin ? "#B45309" : "#FFFBEB";
      stroke = "#B45309";
      radius = 7.5;
    } else if (n.tipo === "destino_almacen") {
      fill = "#0B7A5C";
      stroke = "#0B7A5C";
      radius = 9;
    } else if (isVisited) {
      fill = "#FFFFFF";
      stroke = "#141518";
      radius = 6.5;
    }

    const label = humanNode(n.id);
    const labelWeight = isVisited || n.tipo !== "interseccion" ? "600" : "400";
    const labelColor = isVisited || n.tipo !== "interseccion" ? "#141518" : "#6E7582";
    const linkedOrder = orderByOrigin[n.id] || "";
    const labelY = n.y > 82 ? n.py + 19 : n.py - 12;

    nodesMarkup += `
      <g class="svg-node-group" ${linkedOrder ? `data-origin-order="${linkedOrder}" tabindex="0" role="button" aria-label="Seleccionar proveedor en ${label}"` : ""}>
        ${isSelectedOrigin ? `<circle cx="${n.px}" cy="${n.py}" r="14" fill="rgba(180, 83, 9, 0.14)" />` : ""}
        ${n.tipo === "destino_almacen" ? `<circle cx="${n.px}" cy="${n.py}" r="15" fill="rgba(11, 122, 92, 0.12)" />` : ""}
        <circle cx="${n.px}" cy="${n.py}" r="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="2" />
        <text x="${n.px}" y="${labelY}" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" font-weight="${labelWeight}" fill="${labelColor}" paint-order="stroke" stroke="#FAFAF8" stroke-width="4" stroke-linejoin="round">${label}</text>
      </g>
    `;
  });

  svg.innerHTML = defs + baseLines + highlightLines + nodesMarkup;

  svg.querySelectorAll("[data-origin-order]").forEach((el) => {
    el.addEventListener("click", () => selectOrder(el.dataset.originOrder));
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        selectOrder(el.dataset.originOrder);
      }
    });
  });
}

/* ==========================================================================
   Inspector Causal de Inferencia Lógica (Orden Activa)
   ========================================================================== */

function renderOrderInspector() {
  const container = document.getElementById("orderInspector");
  if (!state.currentSim || !state.selectedOrderId) return;

  const opt = state.currentSim.tareas_optimizadas.find((t) => t.id_pedido === state.selectedOrderId);
  const base = state.currentSim.tareas_base.find((t) => t.id_pedido === state.selectedOrderId);
  if (!opt || !base) return;

  const zoneMeta = ZONE_ACTION_COPY[opt.accion_zona] || {
    badge: opt.accion_zona,
    tone: "neutral",
    detail: "",
  };

  const priorityBadge =
    opt.prioridad_stock === 1
      ? `<span class="pill pill--breach">P1 · Crítico stock</span>`
      : opt.prioridad_stock === 2
      ? `<span class="pill pill--caution">P2 · Preventivo</span>`
      : `<span class="pill pill--neutral">P3 · Regular</span>`;

  const routeSteps = opt.ruta.nodos
    .map((n) => `<span class="corridor-node">${humanNode(n)}</span>`)
    .join(`<span class="corridor-arrow">→</span>`);

  const baseArrivalNote =
    base.ruta.estado_puntualidad === "retrasado"
      ? `Ruta habitual llegaba ${base.ruta.hora_llegada_hhmm} (+${base.ruta.minutos_retraso} min de retraso)`
      : `Ruta habitual llegaba ${base.ruta.hora_llegada_hhmm}`;

  const stockCopy = STOCK_DECISION_COPY[opt.decision_almacen] || opt.decision_almacen;

  container.innerHTML = `
    <div>
      <div class="inspector-top">
        <div>
          <span class="inspector-order-code">${opt.id_pedido} · ${humanCategory(opt.categoria)}</span>
          <h3 class="inspector-supplier">${opt.nombre_proveedor}</h3>
          <span class="inspector-sub">Origen: ${humanNode(opt.origen)} · Salida ${opt.ruta.hora_salida_hhmm} · Plazo máx. ${opt.plazo_maximo_hhmm}</span>
        </div>
        ${priorityBadge}
      </div>
    </div>

    <div class="decision-stack">
      <!-- 1. Decisión Vial -->
      <div class="decision-block">
        <div class="decision-block__head">
          <span class="decision-block__title">1. Inferencia de Ruta (${opt.rutas_evaluadas} evaluadas)</span>
          <span class="pill ${opt.ruta.estado_puntualidad === "a_tiempo" ? "pill--clear" : "pill--caution"}">
            Llegada ${opt.ruta.hora_llegada_hhmm}
          </span>
        </div>
        <div class="corridor-steps">${routeSteps}</div>
        <p class="decision-block__detail">${opt.ruta.distancia_km} km · ${opt.ruta.tiempo_transito_min} min tránsito · ${baseArrivalNote}</p>
      </div>

      <!-- 2. Decisión de Muelle -->
      <div class="decision-block">
        <div class="decision-block__head">
          <span class="decision-block__title">2. Posicionamiento de Muelle</span>
          <span class="pill pill--${zoneMeta.tone}">${zoneMeta.badge}</span>
        </div>
        <div class="decision-block__main">
          ${humanZone(opt.zona_asignada)} · Turno ${opt.ventana_descarga_hhmm}
        </div>
        <p class="decision-block__detail">
          Solicitado: ${humanZone(opt.zona_habitual_proveedor)}. ${zoneMeta.detail}
        </p>
      </div>

      <!-- 3. Decisión de Stock -->
      <div class="decision-block">
        <div class="decision-block__head">
          <span class="decision-block__title">3. Control de Capacidad y Stock</span>
          <span class="pill ${opt.unidades_exceso_evitadas > 0 ? "pill--caution" : "pill--neutral"}">
            ${opt.cantidad_aceptada} / ${opt.cantidad_solicitada} uds
          </span>
        </div>
        <div class="decision-block__main">
          Stock almacén: ${opt.stock_antes} → ${opt.stock_despues} unidades
        </div>
        <p class="decision-block__detail">${stockCopy}</p>
      </div>
    </div>

    <div class="inspector-cost-bar">
      <span class="inspector-sub">Costo integral de la orden</span>
      <div>
        ${base.costo_operativo_total_soles > opt.costo_operativo_total_soles ? `<span class="cost-compare-old">${formatSoles(base.costo_operativo_total_soles)}</span>` : ""}
        <span class="cost-compare-new">${formatSoles(opt.costo_operativo_total_soles)}</span>
      </div>
    </div>
  `;
}

/* ==========================================================================
   Cronograma Visual de Muelles (Gantt 06:50 – 09:50)
   ========================================================================== */

function renderDockGantt() {
  const container = document.getElementById("dockGantt");
  if (!state.snapshot || !state.currentSim) return;

  const span = GANTT_END_MIN - GANTT_START_MIN;
  const tickMarks = [420, 450, 480, 510, 540, 570]; // 07:00 .. 09:30

  const ticksHtml = tickMarks
    .map((m) => {
      const leftPct = ((m - GANTT_START_MIN) / span) * 100;
      return `<span class="gantt-tick" style="left:${leftPct.toFixed(2)}%">${minutesToHhmm(m)}</span>`;
    })
    .join("");

  const zones = state.snapshot.zonas_recepcion;
  const isBaseline = state.ganttMode === "baseline";

  const rowsHtml = zones
    .map((z) => {
      let blocks = [];
      if (!isBaseline) {
        blocks = state.currentSim.tareas_optimizadas
          .filter((t) => t.zona_asignada === z.id_zona)
          .map((t) => ({
            id_pedido: t.id_pedido,
            label: `${t.id_pedido.toUpperCase()} · ${minutesToHhmm(t.inicio_descarga_min)}–${minutesToHhmm(t.fin_descarga_min)}`,
            start: t.inicio_descarga_min,
            end: t.fin_descarga_min,
            conflict: false,
            tooltip: `${t.nombre_proveedor} (${humanCategory(t.categoria)})`,
          }));
      } else {
        blocks = state.currentSim.tareas_base
          .filter((b) => b.zona_intentada === z.id_zona)
          .map((b) => ({
            id_pedido: b.id_pedido,
            label: `${b.id_pedido.toUpperCase()} ${b.error_posicionamiento_zona ? "· INCOMPATIBLE" : b.colapso_zona_recepcion ? "· COLAPSO" : ""}`,
            start: b.inicio_recepcion_min,
            end: b.fin_recepcion_min,
            conflict: b.error_posicionamiento_zona || b.colapso_zona_recepcion,
            tooltip: `${b.nombre_proveedor} — ${b.error_posicionamiento_zona ? "Zona errónea" : b.colapso_zona_recepcion ? "Colisión de muelle" : "Intento habitual"}`,
          }));
      }

      // Asignar sub-carriles visuales si existen bloques solapados (ej. colapso en modo habitual)
      const laneEnds = [];
      blocks.sort((a, b) => a.start - b.start);
      blocks.forEach((blk) => {
        let assignedLane = laneEnds.findIndex((endMin) => endMin <= blk.start);
        if (assignedLane === -1) {
          assignedLane = laneEnds.length;
          laneEnds.push(blk.end);
        } else {
          laneEnds[assignedLane] = blk.end;
        }
        blk.subLane = assignedLane;
      });
      const totalSubLanes = Math.max(1, laneEnds.length);
      const trackHeight = totalSubLanes > 1 ? totalSubLanes * 24 + 6 : 38;

      const barsHtml = blocks
        .map((blk) => {
          const clampedStart = Math.max(GANTT_START_MIN, Math.min(GANTT_END_MIN - 8, blk.start));
          const clampedEnd = Math.min(GANTT_END_MIN, Math.max(clampedStart + 10, blk.end));
          const left = ((clampedStart - GANTT_START_MIN) / span) * 100;
          const width = ((clampedEnd - clampedStart) / span) * 100;
          const selectedCls = blk.id_pedido === state.selectedOrderId ? "is-selected" : "";
          const conflictCls = blk.conflict ? "is-conflict" : "";

          const verticalStyle =
            totalSubLanes > 1
              ? `top:${3 + blk.subLane * 24}px; height:20px; bottom:auto;`
              : "";

          return `
            <button
              type="button"
              class="gantt-bar ${selectedCls} ${conflictCls}"
              style="left:${left.toFixed(2)}%; width:${width.toFixed(2)}%; ${verticalStyle}"
              data-gantt-order="${blk.id_pedido}"
              title="${blk.tooltip}"
            >
              <span>${blk.label}</span>
            </button>
          `;
        })
        .join("");

      return `
        <div class="gantt-row">
          <div class="gantt-dock-label">
            <span class="gantt-dock-name">${humanZone(z.id_zona)}</span>
            <span class="gantt-dock-cap">Cap. simultánea: ${z.capacidad_simultanea} · Máx ${z.capacidad_max_volumen_m3} m³</span>
          </div>
          <div class="gantt-track" style="height:${trackHeight}px">
            ${barsHtml}
          </div>
        </div>
      `;
    })
    .join("");

  container.innerHTML = `
    <div class="gantt-axis">
      <div></div>
      <div class="gantt-ticks">${ticksHtml}</div>
    </div>
    ${rowsHtml}
  `;

  container.querySelectorAll("[data-gantt-order]").forEach((btn) => {
    btn.addEventListener("click", () => selectOrder(btn.dataset.ganttOrder));
  });
}

/* ==========================================================================
   Tabla Manifiesto de Abastecimiento
   ========================================================================== */

function renderManifestTable() {
  const sim = state.currentSim;
  if (!sim) return;

  document.getElementById("manifestCountLabel").textContent = `${sim.tareas_optimizadas.length} órdenes planificadas`;

  const baseById = {};
  sim.tareas_base.forEach((b) => {
    baseById[b.id_pedido] = b;
  });

  const tbody = document.querySelector("#tasksTable tbody");
  tbody.innerHTML = sim.tareas_optimizadas
    .map((t) => {
      const b = baseById[t.id_pedido];
      const isSelected = t.id_pedido === state.selectedOrderId;
      const zoneMeta = ZONE_ACTION_COPY[t.accion_zona] || { badge: t.accion_zona, tone: "neutral" };

      const baseBadge =
        b.ruta.estado_puntualidad === "a_tiempo"
          ? `<span class="pill pill--neutral">${b.ruta.hora_llegada_hhmm}</span>`
          : `<span class="pill pill--breach">${b.ruta.hora_llegada_hhmm} (+${b.ruta.minutos_retraso}m)</span>`;

      const optBadge =
        t.ruta.estado_puntualidad === "a_tiempo"
          ? `<span class="pill pill--clear">${t.ruta.hora_llegada_hhmm} · En plazo</span>`
          : `<span class="pill pill--caution">${t.ruta.hora_llegada_hhmm} (+${t.ruta.minutos_retraso}m)</span>`;

      return `
        <tr class="${isSelected ? "is-selected" : ""}" data-row-order="${t.id_pedido}" tabindex="0">
          <td>
            <span class="cell-primary">${t.nombre_proveedor}</span>
            <span class="cell-sub cell-mono">${t.id_pedido.toUpperCase()} · ${humanNode(t.origen)}</span>
          </td>
          <td>
            <span class="cell-primary">${humanCategory(t.categoria)}</span>
            <span class="cell-sub">Prioridad P${t.prioridad_stock}</span>
          </td>
          <td>${baseBadge}</td>
          <td>${optBadge}</td>
          <td class="cell-mono">${t.plazo_maximo_hhmm}</td>
          <td>
            <span class="cell-primary">${humanZone(t.zona_asignada)}</span>
            <span class="cell-sub">${zoneMeta.badge} (${t.ventana_descarga_hhmm})</span>
          </td>
          <td class="cell-mono">
            ${t.cantidad_aceptada}/${t.cantidad_solicitada} uds
            ${t.unidades_exceso_evitadas > 0 ? `<span class="cell-sub">−${t.unidades_exceso_evitadas} exceso</span>` : ""}
          </td>
          <td class="num-col cell-mono">
            <strong>${formatSoles(t.costo_operativo_total_soles)}</strong>
            <span class="cell-sub">Antes ${formatSoles(b.costo_operativo_total_soles)}</span>
          </td>
        </tr>
      `;
    })
    .join("");

  tbody.querySelectorAll("[data-row-order]").forEach((row) => {
    row.addEventListener("click", () => selectOrder(row.dataset.rowOrder));
    row.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        selectOrder(row.dataset.rowOrder);
      }
    });
  });
}

/* ==========================================================================
   Vista 2: Muelles e Inventario de Almacén
   ========================================================================== */

function renderWarehouseView() {
  if (!state.snapshot || !state.currentSim) return;

  // 1. Tarjetas de especificación de muelles
  const docksGrid = document.getElementById("docksSpecGrid");
  docksGrid.innerHTML = state.snapshot.zonas_recepcion
    .map((z) => {
      const assigned = state.currentSim.tareas_optimizadas.filter((t) => t.zona_asignada === z.id_zona);
      const cats = z.categorias_permitidas
        .map((c) => `<span class="pill pill--neutral">${humanCategory(c)}</span>`)
        .join("");

      return `
        <div class="dock-spec-card">
          <div class="dock-spec-head">
            <span class="dock-spec-title">${humanZone(z.id_zona)}</span>
            <span class="pill ${assigned.length > 0 ? "pill--clear" : "pill--neutral"}">${assigned.length} asignadas</span>
          </div>
          <div class="dock-spec-stats">
            <span>Cupo simultáneo: ${z.capacidad_simultanea}</span>
            <span>Vol. máx: ${z.capacidad_max_volumen_m3} m³</span>
            <span>Descarga: ${z.tiempo_descarga_min} min</span>
          </div>
          <div class="tag-cloud">${cats}</div>
        </div>
      `;
    })
    .join("");

  // 2. Medidores visuales de inventario (aplicando overrides del escenario activo)
  const overridesMap = {};
  (state.currentSim.escenario.stock_overrides || []).forEach((ov) => {
    overridesMap[ov.categoria] = ov;
  });

  const addedByCategory = {};
  const blockedByCategory = {};
  state.currentSim.tareas_optimizadas.forEach((t) => {
    addedByCategory[t.categoria] = (addedByCategory[t.categoria] || 0) + t.cantidad_aceptada;
    blockedByCategory[t.categoria] = (blockedByCategory[t.categoria] || 0) + t.unidades_exceso_evitadas;
  });

  const metersContainer = document.getElementById("inventoryMeters");
  metersContainer.innerHTML = state.snapshot.inventario
    .map((inv) => {
      const ov = overridesMap[inv.categoria] || {};
      const stockBase = ov.stock_actual !== undefined ? ov.stock_actual : inv.stock_actual;
      const stockMin = ov.stock_minimo !== undefined ? ov.stock_minimo : inv.stock_minimo;
      const capMax = ov.capacidad_maxima !== undefined ? ov.capacidad_maxima : inv.capacidad_maxima;

      const added = addedByCategory[inv.categoria] || 0;
      const blocked = blockedByCategory[inv.categoria] || 0;
      const finalStock = Math.min(capMax, stockBase + added);

      const basePct = Math.min(100, (stockBase / capMax) * 100);
      const addedPct = Math.min(100 - basePct, (added / capMax) * 100);
      const minPct = Math.min(100, (stockMin / capMax) * 100);

      const wasCritical = stockBase < stockMin;
      const statusBadge = wasCritical
        ? finalStock >= stockMin
          ? `<span class="pill pill--clear">Quiebre cubierto (${stockBase} → ${finalStock})</span>`
          : `<span class="pill pill--breach">Bajo mínimo (${finalStock} / ${stockMin})</span>`
        : blocked > 0
        ? `<span class="pill pill--caution">Tope protegido (−${blocked} uds exceso)</span>`
        : `<span class="pill pill--neutral">Nivel saludable</span>`;

      return `
        <div class="inv-row">
          <div class="inv-row__top">
            <div>
              <span class="inv-name">${humanCategory(inv.categoria)}</span>
              ${statusBadge}
            </div>
            <span class="inv-figures">
              Inicial: ${stockBase} · Ingreso: +${added} · Final: <strong>${finalStock} / ${capMax} uds</strong> (Mín. ${stockMin})
            </span>
          </div>
          <div class="meter-track" title="Mínimo seguridad: ${stockMin} uds | Capacidad máxima: ${capMax} uds">
            <div class="meter-seg-base" style="width:${basePct.toFixed(2)}%"></div>
            <div class="meter-seg-added" style="width:${addedPct.toFixed(2)}%"></div>
            <div class="meter-min-marker" style="left:${minPct.toFixed(2)}%"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

/* ==========================================================================
   Vista 3: Laboratorio Interactivo de Inferencia Prolog
   ========================================================================== */

async function executePrologLabQuery() {
  const origen = document.getElementById("qOrigen").value;
  const salidaMin = hhmmToMinutes(document.getElementById("qSalida").value);
  const plazoMin = hhmmToMinutes(document.getElementById("qPlazo").value);
  const multa = parseFloat(document.getElementById("qMulta").value) || 0;
  const ventanaMin = Math.max(salidaMin, plazoMin - 30);

  const overrides = [];
  document.querySelectorAll(".lab-traffic-select").forEach((sel) => {
    if (sel.value) {
      const [orig, dest] = sel.dataset.corridor.split("->");
      overrides.push({ origen: orig, destino: dest, nivel: sel.value });
    }
  });

  const btn = document.getElementById("btnRunPrologQuery");
  const out = document.getElementById("routeQueryResults");
  btn.disabled = true;

  try {
    const resp = await fetchJson("/api/v1/routes/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        origen,
        destino: "almacen_central",
        hora_salida_min: salidaMin,
        ventana_inicio_min: ventanaMin,
        plazo_maximo_min: plazoMin,
        multa_por_minuto: multa,
        traffic_overrides: overrides,
      }),
    });

    document.getElementById("labSummarySubtitle").textContent =
      `${resp.total_alternativas} rutas libres de ciclos encontradas desde ${humanNode(origen)} hacia Almacén Santa Anita`;

    if (!resp.alternativas || resp.alternativas.length === 0) {
      out.innerHTML = `<div class="candidate-card">No se hallaron rutas conectadas para los parámetros indicados.</div>`;
      return;
    }

    out.innerHTML = resp.alternativas
      .map((r, idx) => {
        const isBest = idx === 0;
        const steps = r.nodos
          .map((n) => `<span class="corridor-node">${humanNode(n)}</span>`)
          .join(`<span class="corridor-arrow">→</span>`);

        const slaPill =
          r.estado_puntualidad === "a_tiempo"
            ? `<span class="pill pill--clear">En plazo · ${r.hora_llegada_hhmm}</span>`
            : `<span class="pill pill--breach">Retraso +${r.minutos_retraso}m · ${r.hora_llegada_hhmm}</span>`;

        return `
          <article class="candidate-card ${isBest ? "is-optimal" : ""}">
            <div class="candidate-head">
              <div>
                <span class="pill ${isBest ? "pill--clear" : "pill--neutral"}">
                  ${isBest ? "Ruta Óptima Seleccionada" : `Candidata #${idx + 1}`}
                </span>
              </div>
              ${slaPill}
            </div>
            <div class="corridor-steps">${steps}</div>
            <div class="candidate-metrics">
              <span>Distancia: <strong>${r.distancia_km} km</strong></span>
              <span>Tránsito real: <strong>${r.tiempo_transito_min} min</strong></span>
              <span>Transporte: <strong>${formatSoles(r.costo_transporte_soles)}</strong></span>
              <span>Multa SLA: <strong>${formatSoles(r.costo_multa_soles)}</strong></span>
              <span>Costo Total: <strong>${formatSoles(r.costo_total_ruta_soles)}</strong></span>
            </div>
          </article>
        `;
      })
      .join("");
  } catch (err) {
    out.innerHTML = `<div class="candidate-card">${err.message}</div>`;
  } finally {
    btn.disabled = false;
  }
}

function bindLabControls() {
  document.getElementById("routeQueryForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    executePrologLabQuery();
  });

  document.getElementById("btnResetTrafficLab").addEventListener("click", () => {
    document.querySelectorAll(".lab-traffic-select").forEach((sel) => {
      sel.value = "";
    });
    executePrologLabQuery();
  });
}

/* ==========================================================================
   Carga de Escenarios e Inicialización
   ========================================================================== */

async function loadScenario(scenarioId) {
  const errBanner = document.getElementById("errorBanner");
  errBanner.hidden = true;

  try {
    const sim = await fetchJson(`/api/v1/simulate/${scenarioId}`);
    state.currentSim = sim;

    const stillExists = sim.tareas_optimizadas.some((t) => t.id_pedido === state.selectedOrderId);
    if (!stillExists) {
      state.selectedOrderId = sim.tareas_optimizadas[0]?.id_pedido || null;
    }

    renderHeaderAndTelemetry();
    renderSchematicMap();
    renderOrderInspector();
    renderDockGantt();
    renderManifestTable();
    renderWarehouseView();
  } catch (err) {
    document.getElementById("errorMessage").textContent = err.message;
    errBanner.hidden = false;
  }
}

async function initApp() {
  const errBanner = document.getElementById("errorBanner");
  errBanner.hidden = true;

  try {
    const [health, snap, scenResp] = await Promise.all([
      fetchJson("/api/v1/health"),
      fetchJson("/api/v1/snapshot"),
      fetchJson("/api/v1/scenarios"),
    ]);

    state.snapshot = snap;
    state.scenarios = scenResp.scenarios || [];

    const engineName =
      health.prolog && health.prolog.engine === "swi_prolog"
        ? "SWI-Prolog · Activo"
        : "Motor Prolog (.pl) · Activo";
    document.getElementById("engineStatusText").textContent = engineName;

    const select = document.getElementById("scenarioSelect");
    select.innerHTML = state.scenarios
      .map((s) => {
        const shortLabel = s.nombre.replace(/^Escenario\s+\d+:\s*/i, "");
        return `<option value="${s.id}">${shortLabel}</option>`;
      })
      .join("");

    select.addEventListener("change", () => loadScenario(select.value));

    if (state.scenarios.length > 0) {
      await loadScenario(state.scenarios[0].id);
    }
    await executePrologLabQuery();
  } catch (err) {
    document.getElementById("errorMessage").textContent = `Error inicializando FASBIT: ${err.message}`;
    errBanner.hidden = false;
  }
}

document.getElementById("btnRetryInit").addEventListener("click", initApp);
bindNavigation();
bindLabControls();
initApp();
