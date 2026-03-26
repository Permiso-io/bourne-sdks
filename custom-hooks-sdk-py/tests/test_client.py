"""
Tests for PermisoCustomHooksClient.
"""

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from permiso_custom_hooks import PermisoCustomHooksClient, PermisoCustomHooksConfig
from permiso_custom_hooks.exceptions import PermisoCustomHooksError


@pytest.fixture
def config() -> PermisoCustomHooksConfig:
    return PermisoCustomHooksConfig(api_key="test-api-key", base_url="https://api.example.com")


def _ok_response(payload: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = json.dumps(payload or {}).encode("utf-8")
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_sends_request_with_expected_body_shape(config: PermisoCustomHooksConfig) -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(config)
        client.send_event("my_event", {"key": "value"})

    req = mock_urlopen.call_args[0][0]
    assert req.get_full_url() == "https://api.example.com/hooks"
    assert req.headers.get("Content-type") == "application/json"
    assert req.headers.get("X-api-key") == "test-api-key"
    assert req.headers.get("X-hook-source") == "custom"

    body = json.loads(req.data.decode("utf-8"))
    assert set(body.keys()) == {"hookEvent", "runId", "event", "bourneVersion"}
    assert body["hookEvent"] == "my_event"
    assert body["bourneVersion"] == "v2"
    assert body["runId"] == client.get_run_id()
    assert body["event"] == {"key": "value"}
    assert "hook_event_name" not in body
    assert "session_id" not in body


def test_send_event_without_data_sends_empty_event_object(
    config: PermisoCustomHooksConfig,
) -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(config)
        client.send_event("session_start")

    body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
    assert body["hookEvent"] == "session_start"
    assert body["event"] == {}


def test_run_id_is_stable_across_calls(config: PermisoCustomHooksConfig) -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(config)
        run_id = client.get_run_id()
        client.send_event("first")
        client.send_event("second", {"x": 1})

    assert mock_urlopen.call_count == 2
    first_body = json.loads(mock_urlopen.call_args_list[0][0][0].data.decode("utf-8"))
    second_body = json.loads(mock_urlopen.call_args_list[1][0][0].data.decode("utf-8"))
    assert first_body["runId"] == run_id
    assert second_body["runId"] == run_id
    assert client.get_run_id() == run_id


def test_end_run_sends_stop_then_rotates_run_id(config: PermisoCustomHooksConfig) -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(config)
        original_run_id = client.get_run_id()
        client.end_run()

    req = mock_urlopen.call_args[0][0]
    body = json.loads(req.data.decode("utf-8"))
    assert body["hookEvent"] == "stop"
    assert body["runId"] == original_run_id
    assert body["event"] == {"source": "stop"}

    new_run_id = client.get_run_id()
    assert new_run_id != original_run_id
    assert new_run_id


def test_get_run_id_returns_value_from_constructor(config: PermisoCustomHooksConfig) -> None:
    client = PermisoCustomHooksClient(config)
    run_id = client.get_run_id()
    assert isinstance(run_id, str)
    assert run_id


def test_defaults_base_url_when_omitted() -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(PermisoCustomHooksConfig(api_key="test-api-key"))
        client.send_event("event")

    req = mock_urlopen.call_args[0][0]
    assert req.get_full_url() == "https://alb.permiso.io/hooks"


def test_uses_base_url_without_trailing_slash() -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(
            PermisoCustomHooksConfig(api_key="key", base_url="https://api.example.com/")
        )
        client.send_event("event")

    req = mock_urlopen.call_args[0][0]
    assert req.get_full_url() == "https://api.example.com/hooks"


def test_throws_on_non_2xx(config: PermisoCustomHooksConfig) -> None:
    mock_fp = MagicMock()
    mock_fp.read.return_value = json.dumps({"error": "Invalid API key"}).encode("utf-8")
    mock_http_error = HTTPError(
        "https://api.example.com/hooks", 401, "Unauthorized", {}, mock_fp
    )
    mock_http_error.read = mock_fp.read

    with patch("urllib.request.urlopen", side_effect=mock_http_error):
        client = PermisoCustomHooksClient(config)
        with pytest.raises(PermisoCustomHooksError) as exc_info:
            client.send_event("event")

    assert exc_info.value.status == 401
    assert "Invalid API key" in (exc_info.value.body or "")


def test_does_not_rotate_run_id_on_error(config: PermisoCustomHooksConfig) -> None:
    error_resp = HTTPError(
        "https://api.example.com/hooks", 500, "Internal Server Error", {}, MagicMock()
    )
    error_resp.fp = MagicMock()
    error_resp.fp.read.return_value = b""

    with patch("urllib.request.urlopen", side_effect=error_resp):
        client = PermisoCustomHooksClient(config)
        original_run_id = client.get_run_id()
        with pytest.raises(PermisoCustomHooksError):
            client.send_event("event")
        assert client.get_run_id() == original_run_id
        with pytest.raises(PermisoCustomHooksError):
            client.end_run()
        assert client.get_run_id() == original_run_id
