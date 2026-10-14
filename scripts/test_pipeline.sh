#!/usr/bin/env bash

# Weather Intelligence Pipeline Test Runner

set -Eeuo pipefail

# Resolve the Weatherflow project root.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

TEST_DIR="tests"
MODE="${1:-all}"

# Check required tools.
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is not installed or is not on PATH."
    exit 1
fi

if [[ ! -d "$TEST_DIR" ]]; then
    echo "ERROR: Pipeline test directory not found: $TEST_DIR"
    echo "Expected: $PROJECT_ROOT/$TEST_DIR"
    exit 1
fi

if ! uv run pytest --version >/dev/null 2>&1; then
    echo "ERROR: pytest is unavailable."
    echo "Install it with: uv add --dev pytest"
    exit 1
fi

case "$MODE" in
    all)
        echo "Running all Weatherflow pipeline tests..."
        uv run pytest -v "$TEST_DIR"
        ;;

    ingestion)
        echo "Running ingestion tests..."
        uv run pytest -v \
            "$TEST_DIR/test_extract_api.py" \
            "$TEST_DIR/test_state_manager.py" \
            "$TEST_DIR/test_save_json.py"
        ;;

    validation)
        echo "Running weather validation tests..."
        uv run pytest -v \
            "$TEST_DIR/test_weather_validator.py"
        ;;

    transformation)
        echo "Running weather transformation tests..."
        uv run pytest -v \
            "$TEST_DIR/test_weather_transform.py"
        ;;

    storage)
        echo "Running Parquet and PostgreSQL storage tests..."
        uv run pytest -v \
            "$TEST_DIR/test_save_parquet.py" \
            "$TEST_DIR/test_load_postgresql.py"
        ;;

    coverage)
        echo "Running pipeline tests with coverage..."

        if uv run python -c "import pytest_cov" >/dev/null 2>&1; then
            uv run pytest \
                --cov=pipeline \
                --cov-report=term-missing \
                -v "$TEST_DIR"
        else
            echo "ERROR: pytest-cov is not installed."
            echo "Install it with: uv add --dev pytest-cov"
            exit 1
        fi
        ;;

    file)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 file path/to/test_file.py"
            exit 2
        fi

        TEST_FILE="$2"

        if [[ "$TEST_FILE" != /* ]]; then
            TEST_FILE="$PROJECT_ROOT/$TEST_FILE"
        fi

        if [[ ! -f "$TEST_FILE" ]]; then
            echo "ERROR: Test file not found: $TEST_FILE"
            exit 2
        fi

        echo "Running pipeline test file: $TEST_FILE"
        uv run pytest -v "$TEST_FILE"
        ;;

    help|-h|--help)
        cat <<'HELP'
Weatherflow Pipeline Test Runner

Usage:
  ./scripts/test_pipeline.sh [mode]

Modes:
  all             Run all pipeline tests (default)
  ingestion       Test API extraction, state management, and JSON saving
  validation      Test weather data validation
  transformation  Test weather data transformation
  storage         Test Parquet and PostgreSQL loading
  coverage        Run pipeline tests with coverage
  file <path>     Run one test file
  help            Show this help message

Examples:
  ./scripts/test_pipeline.sh
  ./scripts/test_pipeline.sh ingestion
  ./scripts/test_pipeline.sh validation
  ./scripts/test_pipeline.sh transformation
  ./scripts/test_pipeline.sh storage
  ./scripts/test_pipeline.sh coverage
  ./scripts/test_pipeline.sh file pipeline/tests/test_weather_validator.py
HELP
        ;;
    *)
        echo "ERROR: Unknown mode: $MODE"
        echo "Run './scripts/test_pipeline.sh help' for usage."
        exit 2
        ;;
esac
