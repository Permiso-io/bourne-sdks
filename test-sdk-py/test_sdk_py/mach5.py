from __future__ import annotations

import os
import time
from typing import Any, Callable, Literal

from opensearchpy import OpenSearch

EnvName = Literal["staging", "production"]


def _get_env() -> EnvName:
    e = (os.environ.get("MACH5_ENVIRONMENT", "staging") or "staging").lower()
    if e in ("prod", "production"):
        return "production"
    return "staging"


def get_warehouse_name() -> str:
    return (os.environ.get("MACH5_WAREHOUSE") or "perf-test-1").strip() or "perf-test-1"


def get_mach5_index_runs() -> str:
    return (os.environ.get("MACH5_INDEX_RUNS") or "agent_runs_v2").strip() or "agent_runs_v2"


def get_mach5_index_events() -> str:
    default = "agent_run_events_v2"
    return (os.environ.get("MACH5_INDEX_EVENTS") or default).strip() or default


def get_mach5_os_client(
    environment: EnvName | None = None,
    warehouse: str | None = None,
    host: str | None = None,
    timeout: int = 60,
) -> OpenSearch:
    environment = _get_env() if environment is None else environment
    warehouse = get_warehouse_name() if warehouse is None else warehouse
    host = (host or os.environ.get("MACH5_OPENSEARCH_HOST") or "localhost").strip() or "localhost"
    if "MACH5_OPENSEARCH_PORT" in os.environ:
        port = int(os.environ["MACH5_OPENSEARCH_PORT"])
    else:
        port = 9200 if environment == "staging" else 9300
    use_ssl = os.environ.get("MACH5_OPENSEARCH_USE_SSL", "").lower() in ("1", "true", "yes")
    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        url_prefix=f"/warehouse/default/{warehouse}/opensearch",
        use_ssl=use_ssl,
        timeout=timeout,
    )


# Backwards compatibility (default warehouse; prefer get_warehouse_name() for env-driven values)
ENVIRONMENT: EnvName = "staging"
WAREHOUSE_NAME: str = "perf-test-1"


def execute_mach5_os_query(
    index: str,
    body: dict,
    client: OpenSearch,
    **kwargs: Any,
) -> dict:
    return client.search(index=index, body=body, **kwargs)


def search_by_run_id(
    client: OpenSearch,
    run_id: str,
    index: str,
) -> list[dict[str, Any]]:
    res = client.search(
        index=index,
        body={"query": {"term": {"runId": run_id}}, "size": 100},
    )
    return [h["_source"] for h in res.get("hits", {}).get("hits", [])]


def search_events_by_run_id(
    client: OpenSearch,
    run_id: str,
) -> list[dict[str, Any]]:
    return search_by_run_id(client, run_id, get_mach5_index_events())


def search_runs_by_run_id(
    client: OpenSearch,
    run_id: str,
) -> list[dict[str, Any]]:
    return search_by_run_id(client, run_id, get_mach5_index_runs())


def wait_until(
    fn: Callable[[], Any],
    timeout_s: float = 120.0,
    interval_s: float = 2.0,
) -> Any:
    """
    Call ``fn`` until it returns a truthy value, then return that value.
    Raises ``TimeoutError`` on expiry.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        v = fn()
        if v:
            return v
        time.sleep(interval_s)
    raise TimeoutError("wait_until timed out")
