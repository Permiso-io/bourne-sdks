from __future__ import annotations

from permiso_custom_hooks import PermisoCustomHooksConfig

from test_sdk_py.agents import run_planner_subagent_scenario


def test_subagent_parent_and_child_runs(
    captured_http: list[dict],
    base_config: PermisoCustomHooksConfig,
) -> None:
    run_planner_subagent_scenario(
        PermisoCustomHooksConfig(
            api_key=base_config.api_key,
            base_url=base_config.base_url,
            session_id="session-planner-9",
        )
    )

    assert [b["hookEvent"] for b in captured_http] == [
        "user_prompt",
        "plan_draft",
        "critic_subtask",
        "stop",
        "stop",
    ]
    parent_bodies = [captured_http[0], captured_http[1], captured_http[4]]
    child_bodies = [captured_http[2], captured_http[3]]

    parent_id = parent_bodies[0]["runId"]
    for b in parent_bodies:
        assert b["runId"] == parent_id
        assert "parentRunId" not in b

    child_id = child_bodies[0]["runId"]
    assert child_id != parent_id
    for b in child_bodies:
        assert b["runId"] == child_id
        assert b["parentRunId"] == parent_id

    assert all(b.get("sessionId") == "session-planner-9" for b in captured_http)
    assert captured_http[0]["agent"] == {
        "name": "Planner",
        "id": "planner-1",
    }
    assert captured_http[2]["agent"] == {
        "name": "Critic",
        "id": "critic-1",
        "systemPrompt": "Check plans for risk.",
    }
