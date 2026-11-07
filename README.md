# FASBIT — Planificador Lógico y Funcional de Rutas y Recepción de Abastecimiento

Versión preliminar funcional desarrollada para el curso **Programación Lógica y Funcional (UTP - 2026)**.

**Integrantes:**
- Olarte Cortez, José Manuel
- Auccaillo, Miguel Alejandro

---

## Cómo Probar el Proyecto en Visual Studio Code (Sin Complicaciones ni `.exe`)

El proyecto está configurado para ejecutarse directamente desde **Visual Studio Code** en Windows, macOS o Linux **sin necesidad de ejecutar archivos `.exe` manuales**.

> **Nota sobre Prolog:** Si tu computadora tiene instalado **SWI-Prolog (`swipl`)**, el sistema lo detecta y utiliza automáticamente. Si **no** lo tienes instalado aún, FASBIT activa automáticamente su motor lector de archivos `.pl` integrado (`embedded_prolog.py`) leyendo directamente la carpeta `prolog/`, por lo que **funciona de inmediato en cualquier PC que tenga Python 3.11+**.

### Paso 1: Abrir la carpeta en VS Code
1. Abre **Visual Studio Code**.
2. Ve a **Archivo → Abrir carpeta...** (*File → Open Folder...*) y selecciona la carpeta `fasbit`.
3. *(Opcional)* Si VS Code sugiere instalar la extensión oficial de **Python**, acéptala.

### Paso 2: Crear el entorno e instalar librerías (solo la primera vez)
Abre una terminal integrada en VS Code (**Terminal → Nueva terminal** o ``Ctrl + Ñ`` / ``Ctrl + ` ``) y ejecuta:

**Opción A — Usando la paleta visual de VS Code (Recomendado):**
1. Presiona `Ctrl + Shift + P` → escribe **Python: Create Environment** → elige **Venv** → selecciona tu versión de Python → marca **`requirements.txt`** y pulsa Aceptar. VS Code creará `.venv` e instalará todo solo.

**Opción B — Con un solo comando en la terminal de VS Code:**
```bash
python -m pip install -r requirements.txt
```

### Paso 3: Iniciar el Sistema (Elige la forma más cómoda)

* **Con un clic (Botón ▷ o tecla `F5`):**
  1. Abre el archivo **`main.py`** en VS Code y haz clic en el botón **▷ (Run Python File)** arriba a la derecha *(o simplemente presiona **`F5`**)*.
  2. Se iniciará el servidor y **se abrirá automáticamente tu navegador** en `http://127.0.0.1:8000`.
* **Desde la terminal integrada de VS Code:**
  ```bash
  python main.py
  ```

### Comandos Opcionales por Consola (sin interfaz gráfica)
Si deseas ver los reportes directamente en la terminal de VS Code:
```bash
python main.py status
python main.py plan
python main.py simulate
python main.py routes --origen puerto_callao --salida 07:10 --plazo 08:20
```

### Ejecutar las Pruebas Automatizadas
En la barra lateral de VS Code haz clic en el ícono del matraz (**Testing**) y pulsa **▷ Run Tests**, o ejecuta en la terminal:
```bash
python -m pytest -v
```

---

## Propósito del Proyecto

**FASBIT** resuelve la problemática logística de retrasos recurrentes de proveedores, incumplimiento de plazos, posicionamiento incorrecto en muelles, colapsos en zonas de recepción y desbalances de stock mediante una arquitectura híbrida y escalable en **Prolog** y **Python**:

- **Motor Lógico (`prolog/`):** Modela el grafo vial, tráfico por franja horaria, capacidades volumétricas/simultáneas de zonas de recepción y límites de inventario. Aplica reglas de inferencia y búsqueda libre de ciclos para seleccionar rutas óptimas y asignar muelles sin colapsos.
- **Capa Funcional y Aplicativa (`src/fasbit/`):** Procesa resultados sobre estructuras de datos inmutables (`frozen=True`) mediante funciones puras (`map`, `filter`, `reduce`, `pipe`), ejecuta escenarios simulados comparativos y expone una interfaz web minimalista e intuitiva.

---

## Estructura de Carpetas

```text
fasbit/
├── main.py                          # Punto de entrada directo para VS Code (▷ Run / F5 / python main.py)
├── requirements.txt                 # Dependencias ligeras de Python
├── .vscode/                         # Configuración lista para Visual Studio Code (F5, tareas y pruebas)
├── prolog/                          # Capa de Programación Lógica (.pl)
│   ├── main.pl                      # Carga modular del motor lógico
│   ├── knowledge_base/              # Hechos desacoplados por dominio (network, traffic, warehouse, suppliers)
│   ├── rules/                       # Reglas de inferencia (constraints, routing, planner)
│   └── bridge/                      # Puente JSON estructurado stdin/stdout
├── src/fasbit/                      # Capa Funcional y de Aplicación (Python)
│   ├── config.py                    # Configuración y autodetección multiplataforma
│   ├── domain/                      # Modelos inmutables y excepciones de dominio
│   ├── functional/                  # Combinadores funcionales (pipe/compose) y KPIs puros
│   ├── infrastructure/              # PrologBridge + lector embebido .pl + escenarios
│   ├── services/                    # Casos de uso: PlannerService y SimulationService
│   └── interfaces/                  # CLI y API REST + Interfaz Web minimalista
├── data/
│   └── scenarios.json               # 4 escenarios simulados para evaluación de impacto
├── tests/                           # Suite de pruebas automatizadas
└── docs/
    └── architecture.md              # Documentación detallada de arquitectura y trazabilidad
```
