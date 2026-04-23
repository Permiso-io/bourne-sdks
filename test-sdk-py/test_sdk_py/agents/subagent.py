from __future__ import annotations

from permiso_custom_hooks import (
    PermisoAgentContext,
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
)


def run_planner_subagent_scenario(
    config: PermisoCustomHooksConfig,
) -> None:
    """Parent planner delegates to a child critic with its own run_id and parentRunId."""
    parent = PermisoCustomHooksClient(
        PermisoCustomHooksConfig(
            api_key=config.api_key,
            base_url=config.base_url,
            raise_on_error=config.raise_on_error,
            session_id=config.session_id,
            agent=PermisoAgentContext(name="Planner", id="planner-1"),
        )
    )
    parent.send_event(
        "user_prompt",
        {"source": "user", "type": "text", "text": "Outline and critique this plan:"},
    )
    parent.send_event(
        "plan_draft",
        {
            "source": "agent",
            "type": "text",
            "text": "1) research 2) write 3) review",
        },
    )

    child = PermisoCustomHooksClient(
        PermisoCustomHooksConfig(
            api_key=config.api_key,
            base_url=config.base_url,
            raise_on_error=config.raise_on_error,
            parent_run_id=parent.get_run_id(),
            session_id=config.session_id,
            agent=PermisoAgentContext(
                name="Critic",
                id="critic-1",
                system_prompt="Check plans for risk.",
            ),
        )
    )
    child.send_event(
        "critic_subtask",
        {
            "source": "user",
            "type": "text",
            "text": "Review the three steps for safety.",
        },
    )
    child.end_run(stop_reason="end_turn")
    parent.end_run(stop_reason="end_turn")
