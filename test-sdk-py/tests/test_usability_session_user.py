from __future__ import annotations

from permiso_custom_hooks import (
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
)

from test_sdk_py.agents import run_session_user_handoff


def test_session_id_and_set_user_persist(
    captured_http: list[dict],
    base_config: PermisoCustomHooksConfig,
) -> None:
    config = PermisoCustomHooksConfig(
        api_key=base_config.api_key,
        base_url=base_config.base_url,
        session_id="handoff-sess-1",
    )
    run_session_user_handoff(PermisoCustomHooksClient(config))

    b0, b1, b2, b3, b4 = captured_http[0:5]
    for b in captured_http:
        if b.get("user"):
            assert b["user"] == {"id": "user-7", "name": "NewLogin"}
        assert b.get("sessionId") == "handoff-sess-1"

    assert b0.get("user") is None
    assert b1["user"] == {"id": "user-7", "name": "NewLogin"}
    r1 = b0["runId"]
    assert b0["runId"] == b1["runId"] == b2["runId"]
    assert b2["hookEvent"] == "stop"
    assert b3["runId"] not in (r1,)
    assert b3["user"] == {"id": "user-7", "name": "NewLogin"}
    assert b4["runId"] == b3["runId"] and b4["hookEvent"] == "stop"
