# Guía del Sistema `fasbit`

Documento de estudio y sustentación técnica para el curso de **Programación Lógica y Funcional**. Explica el problema logístico resuelto, la arquitectura por capas, las reglas declarativas y cómo los conceptos vistos en clase están integrados directamente dentro de la lógica de negocio sin archivos artificiales.

---

## 1. Problema de Negocio

En el área de recepción logística de un almacén, cada proveedor tiene una **ventana horaria asignada** (cita), un **margen de tolerancia contractual** en minutos, una **tarifa de penalidad por minuto de exceso** en soles (`S/`), una **penalidad fija por inasistencia** y un **nivel de criticidad de stock** (`alta`, `media` o `baja`).

El sistema `fasbit` resuelve de manera determinista tres preguntas para cada entrega del turno:

1. **¿Cómo llegó el proveedor?** Clasifica el arribo en uno de cinco estados (`a_tiempo`, `dentro_de_tolerancia`, `retraso_leve`, `retraso_grave`, `no_presentado`).
2. **¿Qué acción operativa debe tomar almacén?** Cruza el estado de arribo contra la criticidad del stock para decidir la admisión, espera a fin de turno o reprogramación urgente (proponiendo ventanas horarias futuras bajo demanda).
3. **¿Cuál es la multa y el impacto en los KPIs del turno?** Calcula la penalidad exacta en `S/` y consolida puntualidad (*On-Time %*), incidencias, alertas lógicas y desgloses.

---

## 2. Arquitectura por Capas

La aplicación separa estrictamente la lógica pura de la infraestructura web y del almacenamiento:

```text
[Vistas Jinja2 + HTMX]  ──▶  [Controladores Flask]  ──▶  [Servicios (Núcleo Funcional Puro)]
                                      │                                  │
                                      ▼                                  ▼
                           [Repositorios JSON]               [Modelos (@dataclass frozen)]
```

- **Modelos (`src/fasbit/modelos/`):** Solo estructuras de datos inmutables (`@dataclass(frozen=True)`) y constantes de dominio (`ESTADOS_ARRIBO`, `ACCIONES_OPERATIVAS`, `CRITICIDADES_VALIDAS`, `ROLES_VALIDOS`).
- **Repositorios (`src/fasbit/repositorios/`):** Única capa que lee y escribe `data/entregas.json` y `data/usuarios.json`.
- **Servicios (`src/fasbit/servicios/`):** Funciones puras desacopladas de Flask y de archivos. Reciben valores o tuplas inmutables y retornan nuevos valores/tuplas sin efectos secundarios.
- **Controladores (`src/fasbit/controladores/`):** Blueprints de Flask que reciben formularios HTTP/HTMX, invocan repositorios y servicios, y devuelven HTML completo o fragmentos parciales (`hx-swap-oob="true"`).

---

## 3. Conceptos del Curso Aplicados dentro de la Lógica Real

| Concepto del Curso | Dónde vive en `fasbit` | Para qué sirve en el negocio |
| :--- | :--- | :--- |
| **Inmutabilidad** | `modelos/*.py`, `servicios/*.py` | Dataclasses `frozen=True`, `tuple`, `MappingProxyType` y `dataclasses.replace` evitan mutaciones accidentales. |
| **Encaje de patrones (`match/case`) e intervalos** | `sla_servicio.py` (`clasificar_estado_arribo`, `IntervaloMinutos`) | Clasifica el exceso sobre tolerancia usando rangos declarativos (`pertenece_intervalo` / `fuera_de_intervalo`). |
| **Memoización y evaluación perezosa (`yield`)** | `sla_servicio.py` (`@lru_cache`, `_generar_ventanas_infinitas`, `sugerir_ventanas_reprogramacion`) | Evita recalcular horas/reglas repetidas y genera solo las 4 próximas ventanas cuando hay `reprogramacion_urgente`. |
| **Negación por fallo** | `sla_servicio.py` (`es_cumplimiento_sla`) | Define cumplimiento SLA como `estado_arribo in ESTADOS_ARRIBO and not es_incidencia_sla(estado_arribo)`. |
| **Currificación, composición y Functor** | `multa_servicio.py` (`crear_calculador_multa`, `componer`, `Resultado.fmap`, `evaluar_entrega_segura`) | Fija la tarifa contractual del proveedor, encadena evaluación y extracción de multa, y maneja errores sin excepciones en el flujo principal. |
| **`map`, `filter`, `sorted`** | `multa_servicio.py`, `entrega_servicio.py` | Liquida entregas en bloque (`map`), filtra y elimina registros (`filter`) y ordena la tabla del turno (`sorted`). |
| **Recursividad (cadenas, listas y cola)** | `entrega_servicio.py` (`normalizar_codigo_orden`, `buscar_entrega_por_id`) y `kpi_servicio.py` (`acumular_retrasos_cola`) | Normaliza órdenes al crear entregas, busca entregas por ID sobre cabeza/cola y suma retrasos con acumulador de cola. |
| **Reducción y cuantificadores (`∀`, `∃`)** | `kpi_servicio.py` (`calcular_kpis_turno`, `verificar_alertas_turno`) | Consolida las métricas del turno con `functools.reduce` y evalúa consistencia (`all`) y alertas de stock crítico (`any`). |
| **CRUD dinámico en JSON** | `entrega_servicio.py`, `recepcion_controlador.py`, `usuario_controlador.py` | Permite crear, consultar, actualizar llegadas y eliminar entregas (`admin`) en tiempo real. |

---

## 4. Reglas SLA, Matriz 5×3 y Cálculo de Multas

### 4.1 Clasificación de Estado de Arribo

Dado `hora_cita`, `hora_llegada`, `tolerancia_minutos` y `no_presentado`:

- `minutos_retraso = max(0, hora_llegada - hora_cita)` (`0` si `no_presentado=True`).
- `minutos_exceso = max(0, minutos_retraso - tolerancia_minutos)`.

| Condición | Estado resultante | ¿Cuenta como cumplimiento SLA? | ¿Es incidencia? |
| :--- | :--- | :---: | :---: |
| `no_presentado = True` o sin hora de llegada | `no_presentado` | No | Sí |
| `minutos_retraso == 0` | `a_tiempo` | Sí | No |
| `minutos_retraso > 0` y `minutos_exceso == 0` | `dentro_de_tolerancia` | Sí | No |
| `1 <= minutos_exceso <= 30` | `retraso_leve` | No | Sí |
| `minutos_exceso > 30` | `retraso_grave` | No | Sí |

### 4.2 Matriz Declarativa de Decisión Operativa (5 estados × 3 criticidades)

| Estado de arribo | Criticidad `alta` | Criticidad `media` | Criticidad `baja` |
| :--- | :--- | :--- | :--- |
| `a_tiempo` | `admision_prioritaria` | `admision_estandar` | `admision_estandar` |
| `dentro_de_tolerancia` | `admision_prioritaria` | `admision_estandar` | `admision_estandar` |
| `retraso_leve` | `admision_prioritaria` | `admision_estandar` | `recepcion_fin_turno` |
| `retraso_grave` | `reprogramacion_urgente` | `recepcion_fin_turno` | `rechazo_o_cancelacion` |
| `no_presentado` | `reprogramacion_urgente` | `rechazo_o_cancelacion` | `rechazo_o_cancelacion` |

### 4.3 Cálculo Exacto de Multas en Soles (`S/`)

Se usa `decimal.Decimal` con redondeo financiero `ROUND_HALF_UP` a 2 decimales:

- **`a_tiempo` o `dentro_de_tolerancia`:** `S/ 0.00`
- **`retraso_leve` o `retraso_grave`:** `minutos_exceso × tarifa_minuto_soles` (calculado con `crear_calculador_multa`)
- **`no_presentado`:** `penalidad_inasistencia_soles`

**Ejemplo numérico (`ENT-005`):** Cita `09:00`, llegada `09:22`, tolerancia `10` min, tarifa `S/ 6.00/min`, criticidad `alta`:
1. `minutos_retraso = 22 min`
2. `minutos_exceso = 22 - 10 = 12 min` (`<= 30`, por tanto `retraso_leve`)
3. `accion_operativa = admision_prioritaria`
4. `multa_soles = 12 × 6.00 = S/ 72.00`

---

## 5. Mapa Archivo por Archivo

| Archivo | Responsabilidad |
| :--- | :--- |
| `src/fasbit/modelos/proveedor_modelo.py` | Dataclass `Proveedor` y `CRITICIDADES_VALIDAS`. |
| `src/fasbit/modelos/entrega_modelo.py` | Dataclasses `Entrega`, `EvaluacionEntrega` y constantes SLA. |
| `src/fasbit/modelos/usuario_modelo.py` | Dataclass `Usuario` y `ROLES_VALIDOS`. |
| `src/fasbit/repositorios/entrega_repositorio.py` | Carga y guardado UTF-8 de `data/entregas.json`. |
| `src/fasbit/repositorios/usuario_repositorio.py` | Carga y guardado UTF-8 de `data/usuarios.json`. |
| `src/fasbit/servicios/sla_servicio.py` | Parseo `HH:MM` (`@lru_cache`), intervalos, `match/case`, matriz SLA y ventanas perezosas. |
| `src/fasbit/servicios/multa_servicio.py` | Currificación, composición, Functor `Resultado`, `Decimal` y `liquidar_entregas` (`map`). |
| `src/fasbit/servicios/entrega_servicio.py` | Filtros (`filter`), ordenamiento (`sorted`), búsqueda/normalización recursiva y CRUD inmutable. |
| `src/fasbit/servicios/kpi_servicio.py` | Consolidación con `functools.reduce`, recursión de cola y alertas con cuantificadores (`∀`/`∃`). |
| `src/fasbit/servicios/auth_servicio.py` | Hashing `pbkdf2:sha256` y validación de credenciales/roles. |
| `src/fasbit/servicios/usuario_servicio.py` | Reglas de creación, cambio de rol y activación de usuarios. |
| `src/fasbit/controladores/auth_controlador.py` | Login, logout y decoradores `requiere_sesion` / `requiere_rol`. |
| `src/fasbit/controladores/recepcion_controlador.py` | Panel principal, parciales HTMX, evaluación segura (`Resultado`), ventanas y eliminación (`admin`). |
| `src/fasbit/controladores/usuario_controlador.py` | CRUD de cuentas exclusivo para rol `admin`. |
| `src/fasbit/app.py` | Fábrica `crear_app`, filtro `soles`, contexto de sesión y manejo de errores. |

---

## 6. Autenticación y Control de Acceso

- Las contraseñas nunca se almacenan en texto plano; se encriptan con `werkzeug.security.generate_password_hash(..., method="pbkdf2:sha256")`.
- En cada petición (`before_request`), la aplicación valida que el `id_usuario` en sesión siga existiendo y continúe `activo=True`.
- **Rol `admin`:** Acceso total a recepción (incluida eliminación de entregas), evaluador SLA, KPIs y panel `/usuarios`. El sistema impide que el administrador en sesión se desactive a sí mismo, se degrade de rol o desactive al último administrador activo.
- **Rol `operador`:** Acceso operativo completo a `/recepcion` y al evaluador; cualquier petición a `/usuarios` o eliminación de entregas devuelve `403 Forbidden`.
