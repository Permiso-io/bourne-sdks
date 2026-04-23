"""
Tests for PermisoCustomHooksClient.
"""

import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from permiso_custom_hooks import (
    PermisoAgentContext,
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
    PermisoUser,
)
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
    assert {"hookEvent", "runId", "event", "bourneVersion"}.issubset(body.keys())
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
    assert body["event"] == {"source": "stop", "stopReason": "end_turn"}

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


def test_returns_empty_dict_on_non_2xx_when_raise_on_error_false(
    config: PermisoCustomHooksConfig,
) -> None:
    mock_fp = MagicMock()
    mock_fp.read.return_value = json.dumps({"error": "Invalid API key"}).encode("utf-8")
    mock_http_error = HTTPError(
        "https://api.example.com/hooks", 401, "Unauthorized", {}, mock_fp
    )
    mock_http_error.read = mock_fp.read

    with patch("urllib.request.urlopen", side_effect=mock_http_error):
        client = PermisoCustomHooksClient(config)
        result = client.send_event("event")

    assert result == {}


def test_raises_on_non_2xx_when_raise_on_error_true(config: PermisoCustomHooksConfig) -> None:
    mock_fp = MagicMock()
    mock_fp.read.return_value = json.dumps({"error": "Invalid API key"}).encode("utf-8")
    mock_http_error = HTTPError(
        "https://api.example.com/hooks", 401, "Unauthorized", {}, mock_fp
    )
    mock_http_error.read = mock_fp.read

    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key, base_url=config.base_url, raise_on_error=True
    )
    with patch("urllib.request.urlopen", side_effect=mock_http_error):
        client = PermisoCustomHooksClient(cfg)
        with pytest.raises(PermisoCustomHooksError) as exc_info:
            client.send_event("event")

    assert exc_info.value.status == 401
    assert "Invalid API key" in (exc_info.value.body or "")


def test_returns_empty_on_url_error_when_raise_on_error_false(
    config: PermisoCustomHooksConfig,
) -> None:
    with patch(
        "urllib.request.urlopen",
        side_effect=URLError("network down"),
    ):
        client = PermisoCustomHooksClient(config)
        assert client.send_event("event") == {}


def test_does_not_rotate_run_id_on_error_when_raise_true(config: PermisoCustomHooksConfig) -> None:
    error_resp = HTTPError(
        "https://api.example.com/hooks", 500, "Internal Server Error", {}, MagicMock()
    )
    error_resp.fp = MagicMock()
    error_resp.fp.read.return_value = b""

    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key, base_url=config.base_url, raise_on_error=True
    )
    with patch("urllib.request.urlopen", side_effect=error_resp):
        client = PermisoCustomHooksClient(cfg)
        original_run_id = client.get_run_id()
        with pytest.raises(PermisoCustomHooksError):
            client.send_event("event")
        assert client.get_run_id() == original_run_id
        with pytest.raises(PermisoCustomHooksError):
            client.end_run()
        assert client.get_run_id() == original_run_id


def test_end_run_does_not_rotate_on_failure_when_raise_false(
    config: PermisoCustomHooksConfig,
) -> None:
    with patch("urllib.request.urlopen", side_effect=URLError("boom")):
        client = PermisoCustomHooksClient(config)
        rid = client.get_run_id()
        assert client.end_run() == {}
        assert client.get_run_id() == rid


def test_system_prompt_sent_in_agent_single_request(config: PermisoCustomHooksConfig) -> None:
    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key, base_url=config.base_url, system_prompt="Be nice"
    )
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(cfg)
        client.send_event("user_prompt", {"source": "user", "type": "text", "text": "hi"})

    assert mock_urlopen.call_count == 1
    body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
    assert body["agent"] == {"systemPrompt": "Be nice"}
    assert body["hookEvent"] == "user_prompt"


def test_agent_merge_system_prompt_override(config: PermisoCustomHooksConfig) -> None:
    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key,
        base_url=config.base_url,
        agent=PermisoAgentContext(name="A", system_prompt="from-agent"),
        system_prompt="from-top",
    )
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(cfg)
        client.send_event("e1")

    body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
    assert body["agent"] == {"name": "A", "systemPrompt": "from-top"}


def test_parent_run_id_on_wire(config: PermisoCustomHooksConfig) -> None:
    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key,
        base_url=config.base_url,
        parent_run_id="parent-uuid-1",
    )
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(cfg)
        client.send_event("x")

    body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
    assert body["parentRunId"] == "parent-uuid-1"
    assert body["runId"] != "parent-uuid-1"


def test_set_agent_updates_subsequent_requests(config: PermisoCustomHooksConfig) -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(config)
        client.send_event("a")
        client.set_agent(name="Sub", id="sub-9")
        client.send_event("b")

    first = json.loads(mock_urlopen.call_args_list[0][0][0].data.decode("utf-8"))
    assert "agent" not in first

    second = json.loads(mock_urlopen.call_args_list[1][0][0].data.decode("utf-8"))
    assert second["agent"] == {"name": "Sub", "id": "sub-9"}


def test_session_id_from_config_and_set_session_id(
    config: PermisoCustomHooksConfig,
) -> None:
    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key, base_url=config.base_url, session_id="session-a"
    )
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(cfg)
        client.send_event("e1")
        client.set_session_id("session-b")
        client.send_event("e2")
        client.set_session_id(None)
        client.send_event("e3")

    b1, b2, b3 = (
        json.loads(mock_urlopen.call_args_list[i][0][0].data.decode("utf-8"))
        for i in range(3)
    )
    assert b1["sessionId"] == "session-a"
    assert b2["sessionId"] == "session-b"
    assert "sessionId" not in b3


def test_user_config_and_set_user_merge(config: PermisoCustomHooksConfig) -> None:
    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key,
        base_url=config.base_url,
        user=PermisoUser(email="a@x.com", id="u-1", name="Ann"),
    )
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(cfg)
        client.send_event("e1")
        client.set_user(PermisoUser(name="Bea", id="u-2"))  # merge: email from before
        client.send_event("e2")

    b1 = json.loads(mock_urlopen.call_args_list[0][0][0].data.decode("utf-8"))
    b2 = json.loads(mock_urlopen.call_args_list[1][0][0].data.decode("utf-8"))
    assert b1["user"] == {"email": "a@x.com", "id": "u-1", "name": "Ann"}
    assert b2["user"] == {"email": "a@x.com", "id": "u-2", "name": "Bea"}


def test_set_system_prompt_none_clears_agent_key(config: PermisoCustomHooksConfig) -> None:
    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key, base_url=config.base_url, system_prompt="before"
    )
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(cfg)
        client.send_event("e1")
        client.set_system_prompt(None)
        client.send_event("e2", {"source": "user", "type": "text", "text": "x"})

    b2 = json.loads(mock_urlopen.call_args_list[1][0][0].data.decode("utf-8"))
    assert "agent" not in b2


def test_end_run_custom_stop_reason(config: PermisoCustomHooksConfig) -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        client = PermisoCustomHooksClient(config)
        client.end_run(stop_reason="max_tokens")

    body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
    assert body["event"] == {"source": "stop", "stopReason": "max_tokens"}


def test_child_client_parent_run_id_matches_parent(
    config: PermisoCustomHooksConfig,
) -> None:
    with patch("urllib.request.urlopen", return_value=_ok_response()) as mock_urlopen:
        parent = PermisoCustomHooksClient(config)
        parent_id = parent.get_run_id()
        child = PermisoCustomHooksClient(
            PermisoCustomHooksConfig(
                api_key=config.api_key,
                base_url=config.base_url,
                parent_run_id=parent_id,
                agent=PermisoAgentContext(name="Critic", id="c-1"),
            )
        )
        child.send_event("critic_prompt", {"x": 1})
        c_run = child.get_run_id()
        child.send_event("critic_reply")

    c1 = json.loads(mock_urlopen.call_args_list[0][0][0].data.decode("utf-8"))
    c2 = json.loads(mock_urlopen.call_args_list[1][0][0].data.decode("utf-8"))
    assert c1["parentRunId"] == parent_id
    assert c1["runId"] == c2["runId"] == c_run
    assert c1["runId"] != parent_id
    assert c1["agent"] == {"name": "Critic", "id": "c-1"}


def test_send_event_fails_serialization_with_raise(
    config: PermisoCustomHooksConfig,
) -> None:
    cfg = PermisoCustomHooksConfig(
        api_key=config.api_key, base_url=config.base_url, raise_on_error=True
    )
    with patch("urllib.request.urlopen") as mock_urlopen:
        client = PermisoCustomHooksClient(cfg)
        with pytest.raises(PermisoCustomHooksError) as exc_info:
            client.send_event("e", {"bad": object()})
    assert mock_urlopen.call_count == 0
    assert "serialize" in (exc_info.value.message or "")


def test_2xx_empty_response_body_succeeds(config: PermisoCustomHooksConfig) -> None:
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = b""
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp) as mock_urlopen:
        client = PermisoCustomHooksClient(config)
        assert client.send_event("ok") == {}
    assert mock_urlopen.call_count == 1


def test_2xx_invalid_json_response_raises(config: PermisoCustomHooksConfig) -> None:
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = b"not json"
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp):
        client = PermisoCustomHooksClient(
            PermisoCustomHooksConfig(
                api_key=config.api_key, base_url=config.base_url, raise_on_error=True
            )
        )
        with pytest.raises(PermisoCustomHooksError) as exc_info:
            client.send_event("e")
    assert "Invalid JSON" in (exc_info.value.message or "")
    assert exc_info.value.status == 200


def test_2xx_invalid_json_response_returns_empty_when_no_raise(
    config: PermisoCustomHooksConfig,
) -> None:
    resp = MagicMock()
    resp.status = 200
    resp.read.return_value = b"not json"
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=resp):
        client = PermisoCustomHooksClient(config)
        assert client.send_event("e") == {}
