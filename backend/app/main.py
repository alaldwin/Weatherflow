
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import check_database_connection

from app.api.routes.current_weather import router as current_weather_router
from app.api.routes.daily_weather import router as daily_weather_router
from app.api.routes.trends import router as trends_router
from app.api.routes.city_comparison import router as city_comparison_router

from app.core.logging_config import get_logger



logger = get_logger(__name__, "backend_name.log")



app = FastAPI(
    title="Weatherflow API",
    description="API for Weatherflow weather analytics.",
    version="0.1.0",
)

# Register API routers
app.include_router(current_weather_router)
app.include_router(daily_weather_router)
app.include_router(trends_router)
app.include_router(city_comparison_router)


# HTTP request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    try:
        response = await call_next(request)

    except Exception:
        duration = time.perf_counter() - start_time

        logger.exception(
            "Unhandled request error | request_id=%s "
            "method=%s path=%s duration_seconds=%.3f",
            request_id,
            request.method,
            request.url.path,
            duration,
        )
        raise

    duration = time.perf_counter() - start_time

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "Request completed | request_id=%s method=%s "
        "path=%s status_code=%s duration_seconds=%.3f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unexpected application error | method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            }
        },
    )

# Root endpoint
@app.get("/", tags=["General"])
def root():
    return {
        "application": "Weatherflow API",
        "status": "running",
        "docs": "/docs",
    }

# Application health check
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
    }

# Database health check
@app.get("/health/database", tags=["Health"])
def database_health_check():
    try:
        check_database_connection()

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
            },
        )

