# Weatherflow

A small ETL pipeline that extracts current weather for Philippine cities from
[OpenWeather](https://openweathermap.org/), validates it, transforms it into
Polars DataFrames and loads it into JSON files, Parquet files and a PostgreSQL
database.

## Pipeline flow

```
extract (API) -> validate -> transform (Polars) -> save JSON -> save Parquet -> load PostgreSQL
```

`pipeline/main.py` runs every step for each city in `config/cities.py`.

## Requirements

* A reachable PostgreSQL server (the pipeline creates the database and tables for
  you). This can be the PostgreSQL already installed on your machine — the same
  server you register in pgAdmin — or the bundled container.
* Docker (used to run the pipeline against a local PostgreSQL server)
* Python 3.14 + `uv` for local development and tests

## Setup

```bash
# 1. Create your environment file and fill in the API keys + DB password
cp .env.example .env

# 2. Build the pipeline image
docker compose build

# 3. (optional) create the database ahead of time
docker compose run --rm app python -m scripts.create_database

# 4. Run the pipeline: extract -> validate -> transform -> load PostgreSQL
docker compose run --rm app
```

The first run creates the `weatherflow` database if it does not exist and then
creates/refreshes the tables in it. `.env` describes the **host** view of your
PostgreSQL server (`localhost:5432`), while the container reaches the very same
server through `host.docker.internal` — compose sets that automatically.

If you would rather not touch a locally installed server, start the bundled one
instead (published on `5433` so it never clashes with `5432`):

```bash
docker compose --profile localdb up -d db
docker compose --profile localdb run --rm -e POSTGRES_HOST=db app
```

> Always run the pipeline from the project root, the JSON, Parquet and log paths
> are resolved relative to the repository.

## Querying the data in pgAdmin

1. Open pgAdmin and select your server (`PostgreSQL 18` → `localhost:5432`).
2. Right-click **Databases → Refresh** if `weatherflow` is not listed yet.
3. Expand `weatherflow → Schemas → public → Tables` and right-click a table →
   **View/Edit Data → All Rows**.
4. Or use the Query Tool (**Tools → Query Tool**) with the same connection:


# table + row count summary, plus an optional ad-hoc query
docker compose run --rm --no-deps app python -m scripts.inspect_data
docker compose run --rm --no-deps app python -m scripts.inspect_data \
  "SELECT city, temperature FROM openweather_manila;"
```

> **Why a browser does not work:** PostgreSQL is not a web server, so opening
> `http://localhost:5432` always ends in `ERR_CONNECTION_RESET` /
> *"can't reach this page"*. That is expected — use a PostgreSQL client.


## Environment variables

| Variable | Description |
| --- | --- |
| `OPENWEATHER_API_KEY` | OpenWeather API key |
| `POSTGRES_HOST` | Database host as seen from the host machine (default `localhost`) |
| `POSTGRES_PORT` | Database port (default `5432`; bundled container uses `5433`) |
| `POSTGRES_DB` | Database name, created automatically when missing |
| `POSTGRES_USER` | Database user (needs CREATEDB for automatic creation) |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_MAINTENANCE_DB` | Optional, database used to create `POSTGRES_DB` (default `postgres`) |
| `POSTGRES_IF_EXISTS` | Optional loader mode: `replace` (default), `append`, `fail` |
| `APP_POSTGRES_HOST` / `APP_POSTGRES_PORT` | Optional compose overrides for container runs |

## Outputs

| Step | Location |
| --- | --- |
| Raw JSON | `data/openweather/<city>_<YYYY-MM-DD>.json` |
| Transformed Parquet | `data/parquet/<source>/<city>.parquet` |
| PostgreSQL | `openweather_<city>` tables (one per city) |
| Logs | `logs/*.log` |

The load step uses SQLAlchemy with `psycopg2`. The database is created when
missing, tables are created automatically from the DataFrame schema, and new
DataFrame columns are added to an existing table when `POSTGRES_IF_EXISTS=append`
is used. Missing values (`NaN`) are stored as `NULL`.

Check the loaded data with:

```bash
docker compose run --rm --no-deps app python -m scripts.inspect_data
```

## Running the pipeline locally (without Docker)

```bash
uv sync
uv run python -m pipeline.main
```

This only works when the database is reachable **from your shell**. On Windows
with WSL, the native PostgreSQL service is protected by Windows Firewall, so WSL
processes cannot connect to `localhost:5432` even though pgAdmin can. Use
`docker compose run --rm app` (recommended) or follow the troubleshooting entry
below to open a path from WSL.

## Tests

```bash
uv run pytest
```

The test suite covers JSON persistence, validation helpers and the PostgreSQL
loader (using an in-memory SQLite engine that goes through the same SQLAlchemy
code path).

## Troubleshooting

* `can't reach this page` / `ERR_CONNECTION_RESET` in a browser – expected.
  PostgreSQL does not speak HTTP; use pgAdmin or another client (see
  [Querying the data in pgAdmin](#querying-the-data-in-pgadmin)).
* `weatherflow` missing in pgAdmin – right-click **Databases → Refresh**, or run
  `docker compose run --rm app python -m scripts.create_database`.
* `PostgreSQL is not reachable at postgres@localhost:5432/weatherflow` – check
  that the service is running (`Get-Service postgresql*` in PowerShell) and that
  `POSTGRES_PASSWORD` in `.env` matches your `postgres` password.
* **WSL cannot reach a PostgreSQL on Windows** (`connection refused` /
  timeout even though pgAdmin works). Pick one:
  - run the pipeline in a container (`docker compose run --rm app`) — the
    Docker VM is allowed through, or
  - allow the port in an elevated PowerShell:
    `New-NetFirewallRule -DisplayName "WSL PostgreSQL 5432" -Direction Inbound -LocalPort 5432 -Protocol TCP -Action Allow`, or
  - switch WSL to mirrored networking by adding to `C:\Users\<you>\.wslconfig`:
    ```ini
    [wsl2]
    networkingMode=mirrored
    ```
    then `wsl --shutdown` and reopen your terminal (all WSL sessions restart).
* `FATAL: database "weatherflow" does not exist` – you connected to a different
  server than the pipeline wrote to. Compare `POSTGRES_PORT` in `.env` with the
  port shown in pgAdmin (`localhost:5432`).
* Changed the credentials or database after using the bundled container?
  PostgreSQL only applies `POSTGRES_*` on first initialisation, so recreate the
  volume with `docker compose --profile localdb down -v` and start it again.
  **`-v` deletes the volume and all loaded tables.**

