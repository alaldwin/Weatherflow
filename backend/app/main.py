import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.city_comparison import router as city_comparison_router
from app.api.routes.current_weather import router as current_weather_router
from app.api.routes.daily_weather import router as daily_weather_router
from app.api.routes.locations import router as locations_router
from app.api.routes.trends import router as trends_router
from app.api.routes.weather import router as coordinate_weather_router
from app.api.routes.forecast import router as forecast_router

from app.core.logging_config import config_logging, get_logger

from app.db.session import check_database_connection

config_logging()
logger = get_logger(__name__, "backend_main.log")


app = FastAPI(
    title="WeatherFlow API",
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

    OpenWeather APIs → Python ingestion → PostgreSQL → dbt → FastAPI → Weatherflow Mobile App
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(coordinate_weather_router)
app.include_router(current_weather_router)
app.include_router(daily_weather_router)
app.include_router(trends_router)
app.include_router(city_comparison_router) 
app.include_router(locations_router)
app.include_router(forecast_router)



# HTTP request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    # Store the request ID for correlation with other logs.
    request.state.request_id = request_id
    request.state.request_started_at = start_time

    logger.info(
        "http_request_started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    response = await call_next(request)

    duration_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )

    response.headers["X-Request-ID"] = request_id

    log_data = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }

    if response.status_code >= 500:
        logger.error("http_request_completed", extra=log_data)
    elif response.status_code >= 400:
        logger.warning("http_request_completed", extra=log_data)
    else:
        logger.info("http_request_completed", extra=log_data)

    return response

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
        "HTTP response generated | request_id=%s | response_headers=%s",
        request_id,
        response.headers,
    )

    return response


# Standardized HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    request_id = getattr(request.state, "request_id", "unknown")

    error_codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        503: "SERVICE_UNAVAILABLE",
    }

    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", "The request could not be completed.")
        code = exc.detail.get("code", error_codes.get(exc.status_code, "HTTP_ERROR"))
    elif isinstance(exc.detail, str):
        message = exc.detail
        code = error_codes.get(exc.status_code, "HTTP_ERROR")
    else:
        message = "The request could not be completed."
        code = error_codes.get(exc.status_code, "HTTP_ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        headers={
            **(exc.headers or {}),
            "X-Request-ID": request_id,
        },
        content={
            "error": {
                "code": code,
                "message": message,
            },
            "request_id": request_id,
        },
    )


# Standardized request validation handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    request_id = getattr(request.state, "request_id", "unknown")

    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]

    logger.warning(
        "request_validation_failed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 422,
        },
    )

    return JSONResponse(
        status_code=422,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request contains invalid parameters or data.",
                "details": errors,
            },
            "request_id": request_id,
        },
    )


# Standardized unexpected exception handler
@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    request_id = getattr(request.state, "request_id", "unknown")

    start_time = getattr(
        request.state,
        "request_started_at",
        time.perf_counter(),
    )

    duration_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )

    logger.error(
        "http_request_failed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "duration_ms": duration_ms,
        },
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return JSONResponse(
        status_code=500,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            },
            "request_id": request_id,
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
    "/health",
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
                "code": "DATABASE_UNAVAILABLE",
                "message": "The database is currently unavailable.",
            },
        )
