# WeatherFlow — Technology Stack

This document lists the technologies used in WeatherFlow, their roles in the system, and where to verify their configuration in the repository.

> **Scope note:** The stack below is based on the WeatherFlow architecture recorded during development. Package versions and exact deployment details may change; check the current dependency and Docker configuration before publishing exact version claims.

## 1. Stack at a Glance

| Layer | Technology | Role in WeatherFlow |
|---|---|---|
| External data provider | OpenWeather API | Supplies current weather, geocoding/location information, and forecast data where configured |
| Ingestion | Python | Calls provider APIs and coordinates extraction, state checks, transformation, and loading |
| Data transformation | Polars | Processes weather records in tabular form |
| Raw/processed files | JSON and Parquet | JSON stores raw API responses where configured; Parquet stores transformed data artifacts |
| Operational state | Project state manager | Tracks processed observation state to reduce repeated weather processing |
| Database | PostgreSQL | Stores city-specific source records and provides data to downstream models |
| Analytics transformation | dbt Core + dbt-postgres | Builds staging, intermediate, and mart models in PostgreSQL |
| Workflow orchestration | Apache Airflow | Schedules, triggers, and monitors pipeline execution |
| API backend | FastAPI | Exposes weather, location, and health endpoints over HTTP |
| API server | Uvicorn | Runs the ASGI FastAPI application during development or deployment |
| Validation | Pydantic / FastAPI validation | Validates request parameters and structures response data where schemas are defined |
| Mobile frontend | Expo + React Native | Provides the mobile weather dashboard and user interactions |
| Containerization | Docker + Docker Compose | Builds and runs project services in a repeatable local environment |
| Python tooling | `uv` | Manages Python dependencies and executes project commands |
| Testing | pytest | Runs automated Python/backend tests |
| Linting | Ruff | Checks Python code style and common issues |
| Version control | Git | Tracks source code and project documentation |

## 2. Technologies by Layer

### 2.1 External Weather Data

**OpenWeather API**

Used for current weather and geocoding requests. A forecast endpoint has also been under development using OpenWeather's forecast service.

- The API key should be provided through environment configuration.
- Requests that call OpenWeather require network access.
- Timeouts, provider errors, and rate limits should be handled by the relevant client or route.
- Exact endpoints and request parameters should be confirmed in the current extraction and backend code.

### 2.2 Data Ingestion and Processing

**Python**

Coordinates the pipeline: iterates through configured cities, extracts data, checks observation state, invokes transformation components, saves artifacts, and loads records into PostgreSQL.

**Polars**

Used by the project's weather transformation component to process tabular records before persistence.

**JSON and Parquet**

- **JSON:** used for raw API response artifacts where configured.
- **Parquet:** used for transformed data artifacts where configured.

These artifacts support inspection and debugging, but their exact directory layout and retention policy should be checked in the current repository.

### 2.3 Database and Analytics

**PostgreSQL**

Stores weather and geocoding records in city-specific source tables. The known design retains eight `openweather_*` tables and eight corresponding `geocoding_*` tables.

**dbt Core and dbt-postgres**

Transform source tables into analytics-ready models. Known model names include:

- Staging: `stg_weather_observations`, `stg_geocoding_locations`
- Intermediate: `int_city_weather`, `int_daily_weather`
- Marts: `mrt_current_weather`, `mrt_daily_weather`, `mrt_weather_trends`, `mrt_city_comparison`

The mart schema recorded during development is `mrt_dev`. Verify configured targets, actual model dependencies, and materializations in `dbt_weatherflow/`.

### 2.4 Orchestration

**Apache Airflow**

Schedules and monitors pipeline runs. The known DAG ID is `weather_pipeline`, with an hourly schedule recorded during development (`0 * * * *`). Verify the current DAG file, pause state, task graph, and schedule before relying on this value.

Airflow is intended to make recurring execution observable and recoverable. A successful manual run does not prove the scheduled DAG or all downstream tasks are successful.

### 2.5 API Backend

**FastAPI**

Provides HTTP endpoints for current weather, daily summaries, trends, city comparison, location search, health checks, and forecast-related functionality where implemented.

**Uvicorn**

Serves the FastAPI ASGI application. A development command used by the project is:

```bash
uv run uvicorn app.main:app --app-dir backend --reload --log-level info
```

The `--reload` flag is useful during development and should generally be disabled for production execution.

**Pydantic**

FastAPI uses typed parameters and Pydantic schemas to validate inputs and serialize structured responses. The current schema definitions live under `backend/app/schemas/`.

### 2.6 Mobile Application

**Expo and React Native**

Provide the mobile app framework and development workflow. The app communicates with the backend API over HTTP; it should not connect directly to PostgreSQL.

For an Android Studio emulator, the project has used `http://10.0.2.2:8000` to reach a backend running on the host. The correct URL depends on whether the backend runs on the host, inside Docker, or on a physical device.

### 2.7 Containers and Local Development

**Docker and Docker Compose**

Containerize services and provide local service networking. The recorded Compose setup includes PostgreSQL, Airflow, and a backend/pipeline service, but confirm the current `compose.yaml` or `docker-compose.yml` for exact service names, image names, mounts, and published ports.

Typical commands:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100
```

Do not remove Docker volumes unless you intentionally want to delete persisted database data.

### 2.8 Quality and Developer Tools

**uv** — manages Python dependencies and executes project commands.

**pytest** — runs automated tests. The backend previously passed a run of 53 tests; this is a historical result and must be rechecked against the current checkout.

**Ruff** — lints Python code. The project was clean in a prior check; run it again after changes.

**Git** — tracks source code, changes, and documentation.

Example checks:

```bash
uv run pytest -q
uv run ruff check .
```

## 3. Runtime and Networking Notes

The project uses different network addresses depending on the caller:

| Caller | Typical destination | Notes |
|---|---|---|
| Host process calling host-published API | `http://127.0.0.1:8000` | Assumes the backend publishes/listens on port 8000 |
| Android emulator calling host API | `http://10.0.2.2:8000` | Android emulator special alias for the host loopback |
| Container calling PostgreSQL in Compose | `db:5432` | Uses the Compose service name and internal port |
| Host database tool calling PostgreSQL | `localhost:5433` | Assumes Compose maps host port 5433 to container port 5432 |
| Mobile app calling PostgreSQL | Not supported by design | Mobile should call FastAPI instead |

Treat these as recorded development conventions, not guarantees for every launch configuration. Verify actual port mappings in the Compose file.

## 4. Configuration and Secrets

Configuration may be provided through environment variables and local environment files, depending on the component.

- Keep the OpenWeather API key outside source code.
- Keep database passwords and connection URLs out of Git.
- Ensure secret-bearing `.env` files are ignored by version control.
- Confirm that variables are passed to the right Docker Compose service.
- Avoid logging secrets or full authorization headers.

The exact variable names should be verified in the pipeline configuration, `backend/app/core/config.py`, dbt profile, and Compose file.

## 5. Repository Locations to Verify

| Technology / component | Repository location to inspect |
|---|---|
| Python ingestion | `pipeline/` |
| City configuration | `config/cities.py` or the current configured city module |
| PostgreSQL loading | `pipeline/loaded/load_postresql.py` |
| dbt project | `dbt_weatherflow/` |
| Airflow DAG | `airflow/dags/weather_pipeline.py` |
| FastAPI entry point | `backend/app/main.py` |
| API routers | `backend/app/routes/` |
| Database sessions | `backend/app/db/session.py` |
| Backend configuration | `backend/app/core/config.py` |
| Logging | `backend/app/core/logging_config.py` |
| Mobile app | `mobile/` |
| Container setup | `compose.yaml` or `docker-compose.yml`, plus Dockerfiles |
| Python dependencies | `pyproject.toml` and relevant lock files |

File and folder names can differ across branches; confirm them in the current checkout.

## 6. Key Engineering Considerations

- **Idempotency:** append-only loads can produce duplicate rows after retries; consider stable keys and upserts.
- **Observability:** monitor Airflow task status, pipeline failures, API errors, and data freshness.
- **Data quality:** test required fields, valid ranges, uniqueness, and relationships in dbt and Python.
- **Provider resilience:** configure timeouts and sensible retries for OpenWeather calls.
- **Separation of concerns:** keep ingestion, transformation, database access, API logic, and mobile UI responsibilities distinct.
- **Security:** never expose database credentials or provider API keys in the mobile app or public repository.
- **Documentation freshness:** update this file when dependencies, service names, ports, schedules, or architecture change.

## 7. Related Documentation

- [Project Overview](project-overview.md) — goals and end-to-end design.
- [System Architecture](system-architecture.md) — component relationships and runtime flow.
- [Data Flow](data-flow.md) — how records move through the pipeline.
- [Data Dictionary](data-dictionary.md) — weather and geocoding fields.
- [Backend Architecture](backend-architecture.md) — routers, database access, and logging.
