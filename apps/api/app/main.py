from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, logger
from app.core.middleware import SecurityHeadersMiddleware
from app.core.monitoring import capture_exception, configure_sentry
from app.core.rate_limit import limiter

settings = get_settings()
configure_sentry(settings)

app = FastAPI(
    title="CyberComplyIT API",
    description="API della piattaforma di cyber-compliance NIS2/CRA per PMI italiane.",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Normalizza tutte le HTTPException (404, 403, ecc.) in un formato JSON coerente."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Errori di validazione Pydantic (Fase 3: 'middleware di validazione input') in un
    formato leggibile dal frontend, senza esporre dettagli interni dello stack."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Dati non validi", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Error handling globale (Fase 3: 'nessuno stack trace in produzione').

    In sviluppo mostra il messaggio dell'eccezione per facilitare il debug; in produzione
    restituisce solo un messaggio generico, mentre il dettaglio completo finisce comunque nei
    log strutturati (mai perso, solo non esposto al client).
    """
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc!r}")
    capture_exception(exc)
    detail = str(exc) if not settings.is_production else "Errore interno del server"
    return JSONResponse(status_code=500, content={"detail": detail})


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "cybercomplyit-api", "status": "ok"}
