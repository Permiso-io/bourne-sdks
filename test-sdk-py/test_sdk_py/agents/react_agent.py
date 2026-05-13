from __future__ import annotations

from permiso_custom_hooks import PermisoCustomHooksClient

_TOOL_ID = "toolu_react_demo_01"


def run_react_monitoring_scenario(client: PermisoCustomHooksClient) -> None:
    """ReAct loop: user → thinking → tool use/result → assistant, then end run."""
    client.send_event(
        "user_prompt",
        {"source": "user", "type": "text", "text": "What is the status of my order?"},
    )
    client.send_event(
        "support_agent_step",
        {
            "source": "agent",
            "type": "thinking",
            "thinking": "Need to look up order in CRM.",
        },
    )
    client.send_event(
        "crm_lookup",
        {
            "source": "agent",
            "type": "tool_use",
            "name": "lookup_order",
            "toolUseId": _TOOL_ID,
            "input": {"orderId": "ord-7"},
        },
    )
    client.send_event(
        "crm_lookup",
        {
            "source": "agent",
            "type": "tool_result",
            "toolUseId": _TOOL_ID,
            "content": '{"state":"shipped","eta":"2d"}',
        },
    )
    client.send_event(
        "assistant_message",
        {
            "source": "agent",
            "type": "text",
            "text": "Your order is shipped; ETA 2 days.",
            "model": "gpt-4o-mini",
        },
    )
    client.end_run(stop_reason="end_turn")
