
import json
import logging
import uuid
from logging.handlers import RotatingFileHandler
from unittest.mock import Mock

import pytest
from app.core.logging_config import StructuredFormatter
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_health_response_contains_request_id(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")

    # Request IDs should be valid UUIDs.
    uuid.UUID(response.headers["X-Request-ID"])


def test_each_request_has_a_unique_request_id(client):
    first = client.get("/health")
    second = client.get("/health")

    first_id = first.headers.get("X-Request-ID")
    second_id = second.headers.get("X-Request-ID")

    assert first_id
    assert second_id
    assert first_id != second_id


def test_request_completion_log_contains_structured_fields(
    client,
    caplog,
):
    with caplog.at_level(logging.INFO):
        response = client.get("/health")

    assert response.status_code == 200

    records = [
        record
        for record in caplog.records
        if record.getMessage() == "http_request_completed"
    ]

    assert records, "No request completion log was captured."

    record = records[-1]

    assert record.request_id == response.headers["X-Request-ID"]
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0


def test_structured_formatter_outputs_valid_json():
    from app.core.logging_config import StructuredFormatter

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="http_request_completed",
        args=(),
        exc_info=None,
    )

    record.request_id = str(uuid.uuid4())
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 1.25

    output = StructuredFormatter().format(record)
    parsed = json.loads(output)

    assert parsed["message"] == "http_request_completed"
    assert parsed["request_id"] == record.request_id
    assert parsed["method"] == "GET"
    assert parsed["path"] == "/health"
    assert parsed["status_code"] == 200
    assert parsed["duration_ms"] == 1.25
    assert "timestamp" in parsed
    assert parsed["level"] == "INFO"


def test_unexpected_exception_returns_safe_response_with_request_id(
    client,
):
    path = "/__test/unexpected-error"

    def raise_unexpected_error():
        raise RuntimeError("sensitive internal detail")

    app.add_api_route(
        path,
        raise_unexpected_error,
        methods=["GET"],
    )

    try:
        response = client.get(path)

        assert response.status_code == 500

        request_id = response.headers.get("X-Request-ID")
        assert request_id
        uuid.UUID(request_id)

        body = response.json()

        assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert body["error"]["message"] == (
            "An unexpected server error occurred."
        )
        assert "sensitive internal detail" not in response.text

    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != path
        ]


def test_unexpected_error_log_matches_response_request_id(
    client,
    monkeypatch,
):
    from app.main import logger

    path = "/__test/log-correlation"

    def raise_unexpected_error():
        raise RuntimeError("test-only internal failure")

    app.add_api_route(
        path,
        raise_unexpected_error,
        methods=["GET"],
    )

    log_spy = Mock()
    monkeypatch.setattr(logger, "error", log_spy)

    try:
        response = client.get(path)

        assert response.status_code == 500

        request_id = response.headers["X-Request-ID"]

        error_calls = [
            call
            for call in log_spy.call_args_list
            if call.args and call.args[0] == "http_request_failed"
        ]

        assert len(error_calls) == 1

        call = error_calls[0]
        log_fields = call.kwargs["extra"]

        assert log_fields["request_id"] == request_id
        assert log_fields["status_code"] == 500
        assert log_fields["method"] == "GET"
        assert log_fields["path"] == path
        assert call.kwargs["exc_info"] is not None

    finally:
        app.router.routes[:] = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) != path
        ]



def test_rotating_file_handler_creates_backup_logs(tmp_path):
    log_file = tmp_path / "weatherflow-test.log"

    handler = RotatingFileHandler(
        log_file,
        maxBytes=300,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(StructuredFormatter())

    test_logger = logging.getLogger(
        f"weatherflow.rotation.test.{id(handler)}"
    )
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False
    test_logger.addHandler(handler)

    try:
        for index in range(20):
            test_logger.info(
                "rotation_test_event_%s",
                index,
                extra={
                    "request_id": f"test-request-{index}",
                    "method": "GET",
                    "path": "/health",
                    "status_code": 200,
                    "duration_ms": 1.0,
                },
            )

        handler.flush()

        assert log_file.exists()
        assert (tmp_path / "weatherflow-test.log.1").exists()
        assert (tmp_path / "weatherflow-test.log.2").exists()

    finally:
        test_logger.removeHandler(handler)
        handler.close()
