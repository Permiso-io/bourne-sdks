from __future__ import annotations

from permiso_custom_hooks import PermisoCustomHooksClient, PermisoCustomHooksConfig

from test_sdk_py.agents import run_sequential_batch_jobs


def test_sequential_batch_rotates_run_per_job(
    captured_http: list[dict],
    base_config: PermisoCustomHooksConfig,
) -> None:
    run_sequential_batch_jobs(PermisoCustomHooksClient(base_config))

    assert [b["hookEvent"] for b in captured_http] == ["job_event", "stop", "job_event", "stop"]
    a, s1, b, s2 = captured_http
    assert a["runId"] == s1["runId"]
    assert b["runId"] == s2["runId"]
    assert a["runId"] != b["runId"]
    for row in (a, s1, b, s2):
        assert "parentRunId" not in row
