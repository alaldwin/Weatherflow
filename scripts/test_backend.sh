
#!/usr/bin/env bash


# Option	        Meaning
# -E	            Allows error traps to be inherited by certain functions and subshells. It matters mainly when using trap.
# -e	            Exits when a command fails in situations where Bash treats the failure as fatal.
# -u	            Treats references to unset variables as errors.
# -o pipefail	    Makes a pipeline fail if a command within it fails, rather than only checking the last command.

# nable strict error handling
set -Eeuo pipefail 

# Resolve the backend directory from this script's location.

# Find the script's location
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Resolve the backend directory
BACKEND_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# This changes the current working directory to the backend directory
cd "$BACKEND_DIR"

# Check required tools.

# check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is not installed or is not on PATH."
    exit 1
fi

# check if pytest is available
if ! uv run pytest --version >/dev/null 2>&1; then
    echo "ERROR: pytest is unavailable in the backend environment."
    echo "Install it with: uv add --dev pytest"
    exit 1
fi

# Read the selected testing mode
MODE="${1:-all}"

# Choose a mode with case
case "$MODE" in
    # run all backend tests
    all)
        echo "Running All Backend Tests..."
        uv run pytest -v backend/tests
        ;;

    # test weather schemas
    schemas)
        echo "Running Weather Schema Tests..."

        if [[ -f tests/test_weather_schemas.py ]]; then
            uv run pytest -v backend/tests/test_weather_schemas.py
        else
            echo "ERROR: backend/tests/test_weather_schemas.py was not found." >&2
            exit 2
        fi
        ;;

    # test APIs Endpoints
    api)
        echo "Running API tests..."

        if [[ -f tests/test_weather_api.py ]]; then
            uv run pytest -v backend/tests/test_weather_api.py
        else
            echo "ERROR: backend/tests/test_weather_api.py was not found." >&2
            exit 2
        fi
        ;;

    postgres_integration)
        echo "Running PostgreSQL integration tests..."

        if [[ -f tests/test_postgres_integration.py ]]; then
            uv run pytest -v -m integration \
                backend/tests/test_postgres_integration.py
        else
            echo "ERROR: backend/tests/test_postgres_integration.py was not found." >&2
            exit 2
        fi
        ;;

    # measure test coverage
    coverage)
        echo "Running backend tests with coverage..."

        if uv run python -c "import pytest_cov" >/dev/null 2>&1; then
            uv run pytest \
                --cov=app \
                --cov-report=term-missing \
                --cov-report=html \
                -v backend/tests/
        else
            echo "ERROR: pytest-cov is not installed." >&2
            echo "Install it with: uv add --dev pytest-cov" >&2
            exit 1
        fi
        ;;

    # run one test file
    file)
        # first checks that you supplied a file path
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 file path/to/test_file.py"
            exit 2
        fi

        TEST_FILE="$2"

        # Accept paths relative to the backend directory.
        # Also accept paths beginning with backend/ from the project root.
        if [[ ! -f "$TEST_FILE" && -f "$BACKEND_DIR/$TEST_FILE" ]]; then
            TEST_FILE="$BACKEND_DIR/$TEST_FILE"
        elif [[ ! -f "$TEST_FILE" &&
                "$TEST_FILE" == backend/* &&
                -f "$BACKEND_DIR/${TEST_FILE#backend/}" ]]; then
            TEST_FILE="$BACKEND_DIR/${TEST_FILE#backend/}"
        fi

        if [[ ! -f "$TEST_FILE" ]]; then
            echo "ERROR: Test file not found: $2" >&2
            exit 2
        fi

        echo "Running test file: $TEST_FILE"
        uv run pytest -v "$TEST_FILE"
        ;;

    # display instructions
    help|-h|--help)
        cat <<'HELP'
Weatherflow Backend Test Runner

Usage:
    ./scripts/test_backend.sh [mode]
    ./scripts/test_backend.sh file <path>

Modes:
    all                 Run all discovered pytest tests (default)
    schemas             Run weather schema tests
    api                 Run tests under backend/tests/
    postgres_integration  Run PostgreSQL integration tests
    coverage            Run tests with coverage report
    file <path>         Run one test file
    help                Show this help message

Examples:
    ./backend/scripts/test_backend.sh all
    ./backend/scripts/test_backend.sh schemas
    ./backend/scripts/test_backend.sh api
    ./backend/scripts/test_backend.sh postgres_integration
    ./backend/scripts/test_backend.sh coverage
    ./backend/scripts/test_backend.sh file tests/test_postgres_integration.py
    ./backend/scripts/test_backend.sh file backend/tests/test_postgres_integration.py

Examples from the backend directory:
  ./scripts/test_backend.sh all
  ./scripts/test_backend.sh file tests/test_postgres_integration.py
  
HELP
        ;;

    # Handle unknown modes.
    *)
        echo "ERROR: Unknown mode: $MODE" >&2
        echo "Run '$0 help' to see available modes." >&2
        exit 2
        ;;
esac