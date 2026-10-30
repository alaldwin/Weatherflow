#!/usr/bin/env bash

set -Eeuo pipefail

# ==================================================
# WEATHERFLOW - COMPLETE TEST RUNNER
# ==================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

LOG_DIR="logs/tests"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
LOG_FILE="$LOG_DIR/test_run_$TIMESTAMP.log"

mkdir -p "$LOG_DIR"

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

declare -a FAILED_TESTS=()
declare -a SKIPPED_TESTS=()

# Log terminal output and file output
exec > >(tee -a "$LOG_FILE") 2>&1

run_test() {
    local NAME="$1"
    shift

    TOTAL=$((TOTAL + 1))

    echo
    echo "=================================================="
    echo "[$TOTAL] $NAME"
    echo "=================================================="

    local START_TIME=$SECONDS

    if "$@"; then
        local DURATION=$((SECONDS - START_TIME))
        echo "RESULT: PASSED (${DURATION}s)"
        PASSED=$((PASSED + 1))
    else
        local EXIT_CODE=$?
        local DURATION=$((SECONDS - START_TIME))

        echo "RESULT: FAILED (exit code: $EXIT_CODE, ${DURATION}s)"
        FAILED=$((FAILED + 1))
        FAILED_TESTS+=("$NAME")
    fi
}

skip_test() {
    local NAME="$1"

    TOTAL=$((TOTAL + 1))
    SKIPPED=$((SKIPPED + 1))
    SKIPPED_TESTS+=("$NAME")

    echo
    echo "SKIPPED: $NAME"
}

echo "=================================================="
echo " WEATHERFLOW - COMPLETE TEST RUNNER"
echo "=================================================="
echo "Project: $PROJECT_ROOT"
echo "Started: $(date)"
echo "Log: $LOG_FILE"
echo "=================================================="

# --------------------------------------------------
# 1. Shell script syntax tests
# --------------------------------------------------

echo
echo "========== SHELL SCRIPT TESTS =========="

shopt -s nullglob

SHELL_SCRIPTS=(scripts/*.sh)

if ((${#SHELL_SCRIPTS[@]})); then
    for script in "${SHELL_SCRIPTS[@]}"; do
        run_test "Shell syntax: $script" bash -n "$script"
    done
else
    skip_test "Shell script syntax tests (no scripts found)"
fi

# --------------------------------------------------
# 2. Python syntax tests
# --------------------------------------------------

echo
echo "========== PYTHON SYNTAX TESTS =========="

PYTHON_FILES=()

while IFS= read -r -d '' file; do
    PYTHON_FILES+=("$file")
done < <(
    find pipeline backend tests -type f -name "*.py" 
        ! -path "*/.venv/*" 
        ! -path "*/__pycache__/*" 
        -print0 2>/dev/null || true
)

if ((${#PYTHON_FILES[@]})); then
    run_test "Python compilation" python -m compileall -q "${PYTHON_FILES[@]}"
else
    skip_test "Python syntax tests (no Python files found)"
fi

# --------------------------------------------------
# 3. Python unit and integration tests
# --------------------------------------------------

echo
echo "========== PYTEST =========="

if command -v uv >/dev/null 2>&1; then
    if [[ -d tests || -d backend/tests || -d pipeline/tests ]]; then
        run_test "Python pytest" uv run pytest -v
    else
        skip_test "Pytest (no test directories found)"
    fi
elif command -v pytest >/dev/null 2>&1; then
    run_test "Python pytest" pytest -v
else
    skip_test "Pytest (pytest/uv unavailable)"
fi

# --------------------------------------------------
# 4. dbt tests
# --------------------------------------------------

echo
echo "========== DBT TESTS =========="

DBT_PROJECT="dbt_weatherflow"

if [[ -f "$DBT_PROJECT/dbt_project.yml" ]]; then

    if command -v dbt >/dev/null 2>&1; then
        run_test "dbt build" \
            dbt build \
            --project-dir "$DBT_PROJECT" \
            --profiles-dir "$DBT_PROJECT"
    else
        skip_test "dbt build (dbt CLI unavailable)"
    fi

else
    skip_test "dbt tests (dbt project not found)"
fi

# --------------------------------------------------
# 5. Additional shell script tests
# --------------------------------------------------

echo
echo "========== SHELL SCRIPT EXECUTION =========="

for script in "${SHELL_SCRIPTS[@]}"; do

    # Do not execute this central test runner recursively.
    if [[ "$(basename "$script")" == "run_all_tests.sh" ]]; then
        continue
    fi

    run_test "Shell script execution: $script" bash "$script"

done

# --------------------------------------------------
# FINAL SUMMARY
# --------------------------------------------------

echo
echo "=================================================="
echo " WEATHERFLOW - FINAL TEST SUMMARY"
echo "=================================================="

echo "Total:   $TOTAL"
echo "Passed:  $PASSED"
echo "Failed:  $FAILED"
echo "Skipped: $SKIPPED"

echo "Finished: $(date)"

if ((${#FAILED_TESTS[@]})); then
    echo
    echo "FAILED TESTS:"

    for test in "${FAILED_TESTS[@]}"; do
        echo " - $test"
    done
fi

if ((${#SKIPPED_TESTS[@]})); then
    echo
    echo "SKIPPED TESTS:"

    for test in "${SKIPPED_TESTS[@]}"; do
        echo " - $test"
    done
fi

echo
echo "Full log: $LOG_FILE"
echo "=================================================="

if ((FAILED > 0)); then
    echo "SOME TESTS FAILED!"
    exit 1
fi

echo "ALL EXECUTED TESTS PASSED!"
exit 0