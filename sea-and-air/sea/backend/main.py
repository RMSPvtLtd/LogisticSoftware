"""FastAPI application factory for the sea vertical's tracking API.
Registers the centralized domain-error -> HTTP mapping once here, same
pattern as the air vertical -- no route wraps a call in its own try/except.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import tracking
from config import get_settings
from utils.errors import DomainError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Raaziq Sea API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content={"detail": str(exc)})

    app.include_router(tracking.router)

    return app


app = create_app()
