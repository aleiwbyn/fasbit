# fasbit — Control SLA de Recepción Logística

Proyecto universitario para el curso de **Programación Lógica y Funcional** centrado en el control de ventanas horarias (SLA), decisión operativa de admisión en muelle y liquidación automática de penalidades en soles (`S/`) para proveedores logísticos.

## Stack Tecnológico

- **Lenguaje:** Python 3.11+ (100% Python, sin SWI-Prolog)
- **Web y UI reactiva:** Flask + Jinja2 + HTMX + PicoCSS (activos locales en `src/fasbit/static/` para funcionar sin conexión a internet)
- **Seguridad:** Sesiones y hashing `pbkdf2:sha256` nativos de Flask / Werkzeug
- **Persistencia:** Archivos JSON locales (`data/entregas.json` y `data/usuarios.json`)
- **Pruebas:** `pytest`

## Conceptos del Curso Integrados en el Dominio Real

- **Reglas declarativas, intervalos y encaje de patrones (`sla_servicio.py`):** `REGLAS_ACCION_OPERATIVA`, `IntervaloMinutos` (`pertenece_intervalo`/`fuera_de_intervalo`), `match/case` con guardas, negación por fallo (`es_cumplimiento_sla`), memoización con `@lru_cache` y generador perezoso infinito (`sugerir_ventanas_reprogramacion`) cuando una entrega requiere reprogramación urgente.
- **Currificación, composición y Functor (`multa_servicio.py`):** `crear_calculador_multa`, `componer`, transformación funcional con `map()` y contenedor inmutable `Resultado` (`fmap`, `evaluar_entrega_segura`).
- **Recursividad en listas/cadenas y CRUD dinámico (`entrega_servicio.py`):** búsqueda recursiva `buscar_entrega_por_id`, normalización recursiva `normalizar_codigo_orden`, filtrado con `filter()`, ordenamiento con `sorted()`, actualización inmutable con `dataclasses.replace()` y eliminación de entregas (`admin`).
- **Reducción, recursión de cola y cuantificadores (`kpi_servicio.py`):** consolidación con `functools.reduce`, cálculo de retrasos con recursión de cola (`acumular_retrasos_cola`) y alertas operativas del turno mediante cuantificadores `∀` y `∃` (`verificar_alertas_turno`).

## Estructura del Proyecto

```text
fasbit/
├── data/
│   ├── entregas.json
│   └── usuarios.json
├── docs/
│   └── GUIA_SISTEMA.md
├── src/fasbit/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── modelos/            # Estructuras inmutables (@dataclass(frozen=True))
│   ├── repositorios/       # Lectura y escritura JSON
│   ├── servicios/          # Núcleo funcional puro y lógica de negocio
│   ├── controladores/      # Blueprints de Flask
│   ├── templates/          # Vistas Jinja2 y parciales HTMX
│   └── static/             # pico.min.css, htmx.min.js y estilos.css
├── tests/                  # Suite de 5 archivos de pruebas automatizadas
└── pyproject.toml
```

## Instalación y Ejecución

```powershell
# 1. Instalar el paquete en modo editable
pip install -e .

# 2. Iniciar la aplicación web (http://127.0.0.1:5000)
python -m fasbit

# 3. Ejecutar las pruebas unitarias y de integración
pytest -v
```

## Credenciales Semilla de Prueba

| Usuario | Contraseña | Rol | Estado inicial | Permisos |
| :--- | :--- | :--- | :--- | :--- |
| `admin` | `admin123` | `admin` (Jefe de Recepción) | Activo | Control del turno, eliminar entregas, evaluador SLA, KPIs y gestor de usuarios |
| `operador` | `operador123` | `operador` (Auxiliar de Recepción) | Activo | Control del turno, filtros, evaluador SLA y KPIs |
| `operador2` | `lucia123` | `operador` | Inactivo | Cuenta bloqueada para validar rechazo en login |

## Documentación Detallada

Consulta [docs/GUIA_SISTEMA.md](docs/GUIA_SISTEMA.md) para revisar la arquitectura por capas, el detalle de cada concepto del curso aplicado dentro del dominio, la matriz completa de reglas SLA 5×3 y la guía de sustentación.
