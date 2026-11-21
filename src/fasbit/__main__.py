"""Punto de entrada CLI para ejecutar la aplicación web fasbit."""

import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    ruta_src = str(Path(__file__).resolve().parent.parent)
    if ruta_src not in sys.path:
        sys.path.insert(0, ruta_src)

try:
    from fasbit.app import crear_app
except ModuleNotFoundError as exc:
    raise SystemExit(
        f"No se encontró el módulo '{exc.name}'. "
        "Instala las dependencias ejecutando: pip install -r requirements.txt"
    ) from exc


def main() -> None:
    """Inicia el servidor Flask leyendo la configuración desde variables de entorno."""
    app = crear_app()
    host = os.environ.get("FASBIT_HOST", "127.0.0.1")
    puerto = int(os.environ.get("FASBIT_PORT", "5000"))
    depuracion = os.environ.get("FASBIT_DEBUG", "1") == "1"
    app.run(host=host, port=puerto, debug=depuracion)


if __name__ == "__main__":
    main()
