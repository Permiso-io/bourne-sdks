from __future__ import annotations

from permiso_custom_hooks import PermisoCustomHooksClient, PermisoCustomHooksConfig

from test_sdk_py.agents import run_react_monitoring_scenario


def test_react_scenario_event_order_and_tool_id(
    captured_http: list[dict],
    base_config: PermisoCustomHooksConfig,
) -> None:
    client = PermisoCustomHooksClient(base_config)
    run_react_monitoring_scenario(client)

    hooks = [b["hookEvent"] for b in captured_http]
    assert hooks == [
        "user_prompt",
        "support_agent_step",
        "crm_lookup",
        "crm_lookup",
        "assistant_message",
        "stop",
    ]
    # tool_use and tool_result share the same custom hook name and toolUseId
    tool_uses = [b for b in captured_http[2:4] if b["event"].get("type") == "tool_use"]
    tool_res = [b for b in captured_http[2:4] if b["event"].get("type") == "tool_result"]
    assert len(tool_uses) == 1 and len(tool_res) == 1
    assert tool_uses[0]["event"]["toolUseId"] == tool_res[0]["event"]["toolUseId"]
    run_id = captured_http[0]["runId"]
    assert all(b["runId"] == run_id for b in captured_http)
    last = captured_http[-1]
    assert last["hookEvent"] == "stop"
    assert last["event"]["source"] == "stop"
