"""FastAPI application entry point.

Creates the ``FastAPI`` app, registers routers, configures middleware for
structured logging and global exception handlers.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import settings
from .api.routes import router as api_router
from .api.case_detail_routes import router as case_detail_router
from .utils.logging import logger, get_request_id
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI(title="SIH 2026 Identity Screening API", version="0.1.0")

app.include_router(api_router)
app.include_router(case_detail_router)

# Mount the frontend static files after API routers to avoid path conflicts.
# This ensures API endpoints like /api/v1/cases are matched before static file handling.



from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")  # Moved later













from .middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware (uses Redis if configured)
from .middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)


# Middleware to add request_id to logger extra
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = get_request_id(request)
    # Attach to logger for this request – using extra dict
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Health endpoint (outside versioned router for simplicity)
@app.get("/api/v1/health", tags=["health"])
async def health_check():
    return {"status": "ok"}

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("validation_error", extra={"request_id": get_request_id(request), "details": exc.errors()})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error("http_error", extra={"request_id": get_request_id(request), "detail": exc.detail})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# React dashboard (built from frontend/dashboard) — mounted before the legacy
# static frontend so /dashboard/ serves the SPA.
from pathlib import Path as _Path

class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to index.html for client-side routes."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


_dashboard_dist = _Path("frontend/dashboard/dist")
if _dashboard_dist.is_dir():
    app.mount("/dashboard", SPAStaticFiles(directory=str(_dashboard_dist), html=True), name="dashboard")

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("internal_error", extra={"request_id": get_request_id(request), "error": str(exc)})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
