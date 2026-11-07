"""
Punto de entrada universal de FASBIT para Visual Studio Code y terminal.

Formas de uso (sin archivos .exe):
  - Interfaz Web (por defecto al pulsar ▷ Run o F5 en VS Code):
      python main.py
  - Comandos de consola:
      python main.py status
      python main.py plan
      python main.py simulate
      python main.py routes --origen puerto_callao --salida 07:10 --plazo 08:20
"""

from __future__ import annotations

import sys
import threading
import webbrowser
from pathlib import Path

# Garantiza que `src/` esté en sys.path sin requerir `pip install -e .`
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _check_dependencies() -> bool:
    missing: list[str] = []
    for pkg in ("fastapi", "uvicorn", "pydantic"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print("\n" + "=" * 72)
        print("  Faltan librerías de Python para iniciar FASBIT:", ", ".join(missing))
        print("  Ejecuta este único comando en la terminal de VS Code y vuelve a iniciar:")
        print("\n      python -m pip install -r requirements.txt\n")
        print("=" * 72 + "\n")
        return False
    return True


def _launch_web_default(open_browser: bool = True, host: str = "127.0.0.1", port: int = 8000) -> int:
    import uvicorn
    from fasbit.infrastructure.prolog_bridge import PrologBridge
    from fasbit.interfaces.api.app import app

    bridge = PrologBridge()
    url = f"http://{host}:{port}"

    print("\n" + "=" * 72)
    print("  FASBIT — Centro de Despacho y Planificación Lógica")
    print("=" * 72)
    print(f"  Interfaz Web   : {url}")
    print(f"  API Docs       : {url}/docs")
    print(f"  Motor Prolog   : {bridge.swipl_executable}")
    print("  Para detener   : Presiona Ctrl + C en esta terminal")
    print("=" * 72 + "\n")

    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    if not _check_dependencies():
        return 1

    args = sys.argv[1:]

    # Sin argumentos (ej. botón ▷ Run Python File o F5 en VS Code) -> abre Interfaz Web
    if not args or args == ["--no-browser"]:
        return _launch_web_default(open_browser="--no-browser" not in args)

    from fasbit.interfaces.cli import main as cli_main

    return cli_main(args)


if __name__ == "__main__":
    raise SystemExit(main())

