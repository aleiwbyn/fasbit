"""
Configuración centralizada y autodetección de rutas del proyecto y SWI-Prolog.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
PROLOG_MAIN_FILE: Path = PROJECT_ROOT / "prolog" / "main.pl"
SCENARIOS_DATA_FILE: Path = PROJECT_ROOT / "data" / "scenarios.json"
STATIC_WEB_DIR: Path = Path(__file__).resolve().parent / "interfaces" / "api" / "static"


def discover_swipl_executable() -> str | None:
    """
    Localiza el ejecutable de SWI-Prolog (swipl) si está instalado en el sistema.
    Retorna `None` si no se encuentra, permitiendo activar el motor embebido `.pl`
    sin requerir instaladores `.exe` adicionales.
    """
    env_override = os.environ.get("SWIPL_PATH")
    if env_override:
        if env_override.lower() == "none":
            return None
        if Path(env_override).is_file():
            return env_override

    in_path = shutil.which("swipl")
    if in_path:
        return in_path

    candidate_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "swipl" / "bin" / "swipl.exe",
        Path("C:/Program Files/swipl/bin/swipl.exe"),
        Path("C:/Program Files (x86)/swipl/bin/swipl.exe"),
        Path("/opt/homebrew/bin/swipl"),
        Path("/usr/local/bin/swipl"),
        Path("/usr/bin/swipl"),
    ]
    for candidate in candidate_paths:
        if candidate.is_file():
            return str(candidate)

    return None


@dataclass(frozen=True)
class AppSettings:
    """Configuración inmutable de la aplicación."""

    project_root: Path = PROJECT_ROOT
    prolog_entry: Path = PROLOG_MAIN_FILE
    scenarios_file: Path = SCENARIOS_DATA_FILE
    prolog_timeout_sec: int = 15


DEFAULT_SETTINGS = AppSettings()

