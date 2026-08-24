"""FastAPI application factory. Wires the routers together and registers the
centralized exception handlers — every domain error raised anywhere in the
service layer is translated to an HTTP response in exactly one place here,
not by wrapping individual routes in try/except.

Security responsibilities that live here rather than per-route, so a new
route cannot forget them:
  - refusing to boot production with a development secret (config.Settings)
  - security response headers on every response
  - `Cache-Control: no-store`, so confidential business data is never
    written to a shared cache or browser disk cache
  - converting *any* unhandled exception into an opaque 500 carrying only a
    correlation id, so tracebacks/SQL/paths never reach a client
"""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from api import (
    auth,
    companies,
    customer_portal,
    customers,
    documents,
    inquiries,
    invoices,
    meta,
    ops_auth,
    quotes,
    rate_cards,
    shipments,
    tracking,
    worker_portal,
    workers,
)
from config import get_settings
from utils import security_log
from utils.errors import DomainError, DuplicateCustomerEmail

# Applied to every response. This API serves JSON and PDFs only -- it never
# returns HTML a browser would execute -- so the CSP is deliberately the
# most restrictive one that still allows a PDF to render: no scripts, no
# framing, no plugins, no form posts.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    "Content-Security-Policy": (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; object-src 'none'"
    ),
    # Every response carries confidential business data (or an auth error);
    # none of it should be retained by an intermediary or on disk.
    "Cache-Control": "no-store",
}


def create_app() -> FastAPI:
    settings = get_settings()
    # Fails closed: a production deployment still holding a dev JWT secret
    # would be a full authentication bypass, so refuse to start at all.
    settings.assert_production_ready()

    app = FastAPI(
        title="Raaziq API",
        version="0.1.0",
        # Interactive docs enumerate every route and schema. Useful in dev,
        # needless attack-surface/recon in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        # Explicit origins only -- never "*", and never a reflected Origin.
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if settings.is_production:
            # Only meaningful over TLS, and actively harmful to set on a
            # plain-HTTP local dev server.
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response

    @app.exception_handler(DuplicateCustomerEmail)
    def handle_duplicate_customer_email(request: Request, exc: DuplicateCustomerEmail) -> JSONResponse:
        # More specific than the generic DomainError handler below (FastAPI
        # dispatches on the exact exception type first) -- carries the
        # existing customer's id so the frontend can offer to reuse it
        # instead of just showing an error.
        return JSONResponse(
            status_code=exc.http_status,
            content={"detail": str(exc), "customer_id": exc.customer_id, "customer_name": exc.customer_name},
        )

    @app.exception_handler(DomainError)
    def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content={"detail": str(exc)})

    @app.exception_handler(IntegrityError)
    def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # A database constraint (e.g. a duplicate shipment reference) caught
        # what application-level validation didn't. 409 rather than a raw
        # 500, without needing per-endpoint try/except around every write.
        # The driver's message is deliberately dropped: it names tables,
        # columns and constraint names an attacker would use to map the schema.
        return JSONResponse(status_code=409, content={"detail": "The request conflicts with existing data."})

    @app.exception_handler(SQLAlchemyError)
    def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        # Any other database failure (overflow, data error, connection loss).
        # Its `str()` routinely embeds the full parameterized SQL statement.
        error_id = uuid.uuid4().hex[:12]
        security_log.unhandled_error(
            path=request.url.path, method=request.method, error_id=error_id, exc=exc
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "The request could not be completed.", "error_id": error_id},
        )

    @app.exception_handler(Exception)
    def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all so a bug can never surface a traceback, file path, or
        internal message to a client. The full detail is logged server-side
        against `error_id`, which is the only part the caller receives."""
        error_id = uuid.uuid4().hex[:12]
        security_log.unhandled_error(
            path=request.url.path, method=request.method, error_id=error_id, exc=exc
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred.", "error_id": error_id},
        )

    app.include_router(customers.router)
    app.include_router(inquiries.router)
    app.include_router(quotes.router)
    app.include_router(rate_cards.router)
    app.include_router(shipments.router)
    app.include_router(documents.router)
    app.include_router(documents.doc_router)
    app.include_router(companies.router)
    app.include_router(invoices.router)
    app.include_router(invoices.quote_router)
    app.include_router(tracking.router)
    app.include_router(meta.router)
    app.include_router(auth.router)
    app.include_router(ops_auth.router)
    app.include_router(workers.router)
    app.include_router(worker_portal.router)
    app.include_router(customer_portal.router)

    return app


app = create_app()
