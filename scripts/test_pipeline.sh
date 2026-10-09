#!/usr/bin/env bash

# Weather Intelligence Pipeline Test Runner

echo Ingestion Tests

run_test \
    "API Extraction" \
    "uv run pytest tests/test_extract_api.py" \
    || FAILED=1

run_test \
    "State Manager" \
    "uv run pytest tests/test_state_manager.py -v" \
    || FAILED=1

run_test \
    "Save JSON" \
    "uv run pytest tests/test_save_json.py -v" \
    || FAILED=1


echo Validator

run_test \
    "Weather Validator" \
    "uv run pytest tests\test_weather_validator.py -v " \
    || FAILED=1

