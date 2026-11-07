"""
Aplicación FastAPI principal con soporte de Dashboard Web estático.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fasbit.config import STATIC_WEB_DIR
from fasbit.interfaces.api.routes import router as api_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="FASBIT - Planificador Lógico y Funcional de Abastecimiento",
        description=(
            "Sistema preliminar de optimización de rutas de proveedores, control de zonas "
            "de recepción y gestión preventiva de stock mediante SWI-Prolog y Python."
        ),
        version="0.1.0",
    )

    application.include_router(api_router)

    if STATIC_WEB_DIR.is_dir():
        application.mount("/static", StaticFiles(directory=str(STATIC_WEB_DIR)), name="static")

        @application.get("/", include_in_schema=False)
        def serve_dashboard() -> FileResponse:
            return FileResponse(str(STATIC_WEB_DIR / "index.html"))

    return application


app = create_app()

