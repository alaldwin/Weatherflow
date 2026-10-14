
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
    description="""
    # Weatherflow Weather Intelligence API

    Provides current weather, daily weather summaries, weather trends,
    and city comparisons using processed weather data stored in PostgreSQL.

    ## Main features

    - Current weather by city
    - Daily weather filtering by city and date range
    - Historical weather trends
    - Weather comparisons across cities

    ## Data flow

    OpenWeather APIs → Python ingestion → PostgreSQL → dbt → FastAPI
    """,
    version="1.0.0",
    contact={
        "name": "Weatherflow Project",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Check API availability and database connectivity.",
        },
        {
            "name": "Current Weather",
            "description": "Retrieve the latest processed weather observations.",
        },
        {
            "name": "Daily Weather",
            "description": "Retrieve daily weather summaries with optional filters.",
        },
        {
            "name": "Weather Trends",
            "description": "Review historical changes in temperature and humidity.",
        },
        {
            "name": "City Comparison",
            "description": "Compare current weather conditions across cities.",
        },
    ],
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

    # Store the request ID for correlation with other logs.
    request.state.request_id = request_id

    logger.debug(
        "Incoming HTTP request | request_id=%s | method=%s | path=%s",
        request_id,
        request.method,
        request.url.path,
    )

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

    log_message = (
        "Request completed | request_id=%s | method=%s | "
        "path=%s | status_code=%s | duration_seconds=%.3f"
    )

    log_args = (
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    if response.status_code >= 500:
        logger.error(log_message, *log_args)

    elif response.status_code >= 400:
        logger.warning(log_message, *log_args)

    else:
        logger.info(log_message, *log_args)

    logger.debug(
        "HTTP response generated | request_id=%s | "
        "response_headers=%s",
        request_id,
        response.headers,
    )

    return response



# Global exception handler
@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    request_id = getattr(request.state, "request_id", "unknown")

    logger.exception(
        "Unexpected application error | request_id=%s | "
        "method=%s | path=%s",
        request_id,
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

    logger.debug("Root endpoint requested")

    logger.info("Weatherflow API root endpoint accessed")

    return {
        "application": "Weatherflow API",
        "status": "running",
        "docs": "/docs",
    }



# Application health check
@app.get(
    tags=["Health"],
    summary="Check API health",
    description="Confirms that the FastAPI application is responding.",
)
def health_check():

    logger.debug("Application health check started")

    logger.info("Application health check successful")

    return {
        "status": "healthy",
    }



# Database health check
@app.get(
    "/health/database",
    tags=["Health"],
    summary="Check database connectivity",
    description="Checks whether the backend can execute a query against PostgreSQL.",
)
def database_health_check():

    logger.debug("Database health check started")

    try:
        check_database_connection()

        logger.info("Database health check successful")

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
            },
        )

