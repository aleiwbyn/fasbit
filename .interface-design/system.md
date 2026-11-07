# FASBIT Design System (`interface-design`)

## 1. Direction & Intent
- **Persona & Moment:** Supply-chain dispatch coordinator & logistics engineer reviewing morning supplier arrivals (Lima/Callao → Santa Anita) before rush-hour cutoffs.
- **Core Verb:** Verify, trace, and simulate — understand at a glance how SWI-Prolog resolved route congestion, dock collisions, wrong-dock assignments, and warehouse stock limits.
- **Feel:** Precision Swiss dispatch board on warm mineral paper — calm, architectural, ultra-legible, minimal. Structure is carried by space, typography, and hairline borders; color appears strictly as operational signal.

## 2. Domain & Signature
- **Domain Vocabulary:** Manifiesto de despacho, muelle/andén de descarga, ventana SLA, corredor arterial, tope de estiba, quiebre de stock, traza de inferencia lógica.
- **Signature Elements:**
  1. **Dual-Corridor Lima Schematic + Causal Inference Inspector:** Displays discarded habitual path (crimson dashed) vs Prolog optimal path (emerald solid) alongside a 3-part causal breakdown (Vial · Muelle · Estiba).
  2. **Synchronized Time-Axis Dock Gantt (07:00–09:45):** Proportional horizontal swimlanes per reception dock with an instant toggle to preview the unoptimized collision/wrong-zone state vs FASBIT's collision-free schedule.
- **Rejected Defaults:**
  - Generic dark-slate `#0f172a` AI dashboard → Warm mineral paper (`#F6F6F3`) + crisp white sheets (`#FFFFFF`).
  - 4 separate floating KPI boxes → Unified 4-column Telemetry Strip divided by `1px` hairlines.
  - Raw snake_case backend strings → Human-crafted Spanish logistics microcopy.

## 3. Token Architecture
- **Surfaces (single warm hue ~48°, low chroma):**
  - `--paper-canvas: #F6F6F3` (page canvas)
  - `--sheet-surface: #FFFFFF` (elevated containers)
  - `--sheet-subtle: #FAFAF8` (secondary panels / map stage)
  - `--well-inset: #EFEFEB` (inputs, segmented controls, progress tracks)
- **Ink Hierarchy (4 levels):**
  - `--ink-primary: #141518`
  - `--ink-secondary: #4A505C`
  - `--ink-tertiary: #6E7582`
  - `--ink-muted: #949BA6`
- **Borders (Depth Strategy: Borders-only + tonal shift):**
  - `--hairline-subtle: rgba(20, 21, 24, 0.06)`
  - `--hairline-default: rgba(20, 21, 24, 0.10)`
  - `--hairline-strong: rgba(20, 21, 24, 0.18)`
- **Operational Signals (~10% screen budget):**
  - `--signal-logic: #1D4ED8` (interactive focus & Prolog inference)
  - `--signal-clear: #0B7A5C` / `--signal-clear-tint: #ECFDF5` (on-time, optimal corridor, valid dock)
  - `--signal-caution: #B45309` / `--signal-caution-tint: #FFFBEB` (supplier origin, preventive stock, dock shift)
  - `--signal-breach: #BE123C` / `--signal-breach-tint: #FFF1F2` (habitual delay, dock collision, critical stockout)

## 4. Typography, Spacing & Radii
- **Font Stack:** `'Inter', system-ui, -apple-system, sans-serif` + `'JetBrains Mono', 'Cascadia Mono', Consolas, monospace` for timestamps, order IDs, PEN currency, and distances.
- **Type Scale (1.25 ratio):** `11px` (eyebrow/tracked) · `13px` (dense table/captions) · `14px` (body) · `16px` (panel titles) · `20px` (section headers) · `28px` (hero telemetry `tabular-nums`).
- **Spacing Grid:** `4px` base (`4, 8, 12, 16, 20, 24, 32, 40px`).
- **Concentric Radii:** `--radius-sm: 6px` (buttons, inputs, badges) · `--radius-md: 10px` (inner wells, inspector blocks) · `--radius-lg: 14px` (outer sheets).

## 5. Key Component Measurements
- **Topbar:** `56px` height · sticky · `1px` bottom hairline · segmented nav pills (`36px` height, `4px` inset track).
- **Telemetry Strip:** `14px` outer radius · `20px 24px` cell padding · `28px/600` tabular metric + inline delta badge.
- **Buttons & Controls:** `40px` min hit height · `0 14px` padding · `6px` radius · `:active` `scale(0.98)` at `140ms cubic-bezier(0.23, 1, 0.32, 1)`.
- **Dock Gantt Swimlane:** `44px` lane height · proportional percentage positioning across `[410, 590]` min (`06:50`–`09:50`).

