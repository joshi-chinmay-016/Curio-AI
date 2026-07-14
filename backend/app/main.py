import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import setup_logging
from backend.app.api.router import api_router

setup_logging()
logger = logging.getLogger("curio_main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register Exception Handlers
register_exception_handlers(app)

# Health endpoint at root level
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "connected"  # In a real environment, we'd ping the DB
    }

# Register Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

logger.info("Curio AI backend successfully initialized.")
