"""FastAPI application factory. Wires the routers together and registers the
centralized exception handlers — every domain error raised anywhere in the
service layer is translated to an HTTP response in exactly one place here,
not by wrapping individual routes in try/except.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from api import (
    auth,
    customer_portal,
    customers,
    inquiries,
    meta,
    quotes,
    shipments,
    tracking,
    worker_portal,
    workers,
)
from config import get_settings
from utils.errors import DomainError


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Raaziq API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content={"detail": str(exc)})

    @app.exception_handler(IntegrityError)
    def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # A database constraint (e.g. a duplicate shipment reference) caught
        # what application-level validation didn't. 409 rather than a raw
        # 500, without needing per-endpoint try/except around every write.
        return JSONResponse(status_code=409, content={"detail": "The request conflicts with existing data."})

    app.include_router(customers.router)
    app.include_router(inquiries.router)
    app.include_router(quotes.router)
    app.include_router(shipments.router)
    app.include_router(tracking.router)
    app.include_router(meta.router)
    app.include_router(auth.router)
    app.include_router(workers.router)
    app.include_router(worker_portal.router)
    app.include_router(customer_portal.router)

    return app


app = create_app()
