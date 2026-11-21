"""Punto de entrada CLI para ejecutar la aplicación web fasbit."""

import os

from fasbit.app import crear_app


def main() -> None:
    """Inicia el servidor Flask leyendo la configuración desde variables de entorno."""
    app = crear_app()
    host = os.environ.get("FASBIT_HOST", "127.0.0.1")
    puerto = int(os.environ.get("FASBIT_PORT", "5000"))
    depuracion = os.environ.get("FASBIT_DEBUG", "1") == "1"
    app.run(host=host, port=puerto, debug=depuracion)


if __name__ == "__main__":
    main()
