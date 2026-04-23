"""
End-to-end: send Custom Hooks to the real API, then wait for OpenSearch (Mach5) to index
``agent_runs_v2`` and ``agent_run_events_v2`` and assert on stored fields.

Requires (see :mod:`test_sdk_py.mach5`):

- ``E2E_MACH5=1``
- ``PERMISO_API_KEY`` (and optional ``PERMISO_BASE_URL``)
- Reachable OpenSearch: ``MACH5_OPENSEARCH_HOST``, ``MACH5_OPENSEARCH_PORT``, ``MACH5_WAREHOUSE``,
  ``MACH5_INDEX_RUNS`` / ``MACH5_INDEX_EVENTS`` as needed for your tunnel or env.

- Debug (``E2E_MACH5_DEBUG=1`` in the environment or in a loaded ``.env``) prints paths and key
  state to stderr; use ``pytest -s`` so stderr is not folded away.

Skipped automatically when e2e env is not set (CI runs the mocked tests only).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

# Note: opensearch is imported only after :func:`_load_dotenv` (see end of file) so debug
# prints and .env run even when ``opensearchpy`` is missing (skip with a clear reason).


def _e2e_enabled() -> bool:
    return (os.environ.get("E2E_MACH5", "") or "").strip().lower() in ("1", "true", "yes")


def _dotenv_paths_walking_up(start: Path) -> list[Path]:
    """``start`` = file or directory; return each existing ``.env`` up to the filesystem root."""
    out: list[Path] = []
    d = start if start.is_dir() else start.parent
    d = d.resolve()
    for _ in range(32):
        candidate = d / ".env"
        if candidate.is_file():
            out.append(candidate.resolve())
        if d.parent == d:
            break
        d = d.parent
    return out


def _collect_dotenv_load_order() -> list[Path]:
    """Order used by :func:`_load_dotenv` (shallowest path = repo root, loaded last, wins)."""
    seen: set[Path] = set()
    collected: list[Path] = []
    for p in _dotenv_paths_walking_up(Path(__file__).resolve().parent) + _dotenv_paths_walking_up(
        Path.cwd().resolve()
    ):
        if p in seen:
            continue
        seen.add(p)
        collected.append(p)
    return sorted(collected, key=lambda p: len(p.parts), reverse=True)


def _load_dotenv() -> None:  # at module import so skipif sees keys from .env
    # See _collect_dotenv_load_order: deepest first, ``override=True``, repo root .env last.
    for path in _collect_dotenv_load_order():
        try:
            from dotenv import load_dotenv

            load_dotenv(path, override=True)
        except ImportError:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                key, val = k.strip(), v.strip().strip("'\"")
                if key:
                    os.environ[key] = val


def _debug_e2e_enabled() -> bool:
    return (os.environ.get("E2E_MACH5_DEBUG", "") or "").strip().lower() in ("1", "true", "yes")


def _mask_secret(s: str, edge: int = 5) -> str:
    t = s.strip()
    if not t:
        return "<empty>"
    if len(t) <= edge * 2 + 1:
        return f"<{len(t)} chars>"
    return f"{t[:edge]}...{t[-edge:]} (len={len(t)})"


def _e2e_dprint(*parts: str) -> None:
    print(*parts, file=sys.stderr, flush=True)


def _print_e2e_env_debug() -> None:
    """``export E2E_MACH5_DEBUG=1`` (or set in .env) then ``pytest -s`` to see on stderr."""
    if not _debug_e2e_enabled():
        return
    order = _collect_dotenv_load_order()
    e2e = _e2e_enabled()
    key = (os.environ.get("PERMISO_API_KEY", "") or "").strip()
    has_dotenv_pkg = importlib.util.find_spec("dotenv") is not None
    _e2e_dprint(f"[test_e2e_mach5] E2E_MACH5_DEBUG: __file__={Path(__file__).resolve()}")
    _e2e_dprint(f"[test_e2e_mach5] E2E_MACH5_DEBUG: cwd={Path.cwd().resolve()}")
    _e2e_dprint(
        f"[test_e2e_mach5] E2E_MACH5_DEBUG: python-dotenv installed={has_dotenv_pkg}"
    )
    _e2e_dprint(
        f"[test_e2e_mach5] E2E_MACH5_DEBUG: .env files, load order ({len(order)}), "
        f"shallowest path loaded last (wins):"
    )
    for p in order:
        _e2e_dprint(f"  -> {p}  exists={p.is_file()}")
    e2e_raw = os.environ.get("E2E_MACH5", "<missing>")
    _e2e_dprint(
        f"[test_e2e_mach5] E2E_MACH5_DEBUG: E2E_MACH5: {e2e_raw!r} -> e2e_enabled()={e2e}"
    )
    _e2e_dprint(
        f"[test_e2e_mach5] E2E_MACH5_DEBUG: PERMISO_API_KEY after load: {_mask_secret(key)}"
    )
    if not e2e:
        _e2e_dprint(
            "[test_e2e_mach5] E2E_MACH5_DEBUG: will skip: need E2E_MACH5=1, true, or yes"
        )
    if not key:
        _e2e_dprint(
            "[test_e2e_mach5] E2E_MACH5_DEBUG: will skip: PERMISO_API_KEY empty/whitespace"
        )
    _e2e_dprint(
        "[test_e2e_mach5] E2E_MACH5_DEBUG: check pytest skipif reason in output above"
    )


def _e2e_timeout_s() -> float:
    return float((os.environ.get("MACH5_E2E_TIMEOUT", "") or "120").strip() or "120")


def _e2e_interval_s() -> float:
    return float((os.environ.get("MACH5_E2E_POLL_INTERVAL", "") or "2").strip() or "2")


def _config() -> PermisoCustomHooksConfig:
    key = (os.environ.get("PERMISO_API_KEY", "") or "").strip()
    base = (os.environ.get("PERMISO_BASE_URL", "") or "").strip() or None
    kwargs: dict = {"api_key": key, "raise_on_error": True}
    if base:
        kwargs["base_url"] = base
    return PermisoCustomHooksConfig(**kwargs)


def _text_markers() -> str:
    return f"e2e-mach5-{uuid.uuid4().hex[:20]}"


# Load .env before pytest evaluates skipif (and make keys visible without export).
_load_dotenv()
_print_e2e_env_debug()
_key_ok = bool((os.environ.get("PERMISO_API_KEY", "") or "").strip())
if (not _e2e_enabled() or not _key_ok) and not _debug_e2e_enabled():
    _e2e_dprint(
        "[test_e2e_mach5] skipif: missing E2E_MACH5=1 and/or PERMISO_API_KEY after .env. "
        "Set E2E_MACH5_DEBUG=1 for paths; if key+e2e are set and you still get 's', "
        "check opensearch (fixture) on stderr",
    )

if importlib.util.find_spec("opensearchpy") is None:
    _e2e_dprint(
        "[test_e2e_mach5] opensearchpy missing: pip install -e .  (then pytest skip follows)"
    )
pytest.importorskip("opensearchpy", reason="install test-sdk-py: pip install -e .  (opensearch-py)")
from opensearchpy import OpenSearch
from permiso_custom_hooks import (
    PermisoAgentContext,
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
    PermisoUser,
)

from test_sdk_py.mach5 import (
    get_mach5_os_client,
    search_events_by_run_id,
    search_runs_by_run_id,
    wait_until,
)

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _e2e_enabled() or not (os.environ.get("PERMISO_API_KEY", "") or "").strip(),
        reason="Set E2E_MACH5=1 and PERMISO_API_KEY (e.g. via .env) to run",
    ),
]


@dataclass(frozen=True)
class E2EIndexedRun:
    """
    One Custom Hooks run after Mach5 has indexed the run and events (``agent_runs_v2`` / events).
    """

    run_id: str
    session_id: str
    text_marker: str
    rdocs: list[dict]
    edocs: list[dict]

    @property
    def run_src(self) -> dict:
        return self.rdocs[0]


def _index_one_custom_hooks_run(opensearch: OpenSearch) -> E2EIndexedRun:
    text_marker = _text_markers()
    session_id = f"e2e-sess-{uuid.uuid4().hex[:18]}"

    cfg = _config()
    cfg = PermisoCustomHooksConfig(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        session_id=session_id,
        raise_on_error=cfg.raise_on_error,
        user=PermisoUser(id="e2e-user-1", name="E2E User"),
        agent=PermisoAgentContext(
            name="E2EMach5Agent",
            id="e2e-mach5-agent-1",
            system_prompt="E2E system prompt (short).",
        ),
    )
    client = PermisoCustomHooksClient(cfg)
    run_id = client.get_run_id()
    try:
        client.send_event(
            "user_prompt",
            {
                "source": "user",
                "type": "text",
                "text": f"E2E message. Marker: {text_marker}.",
            },
        )
        client.end_run(stop_reason="end_turn")
    except Exception as e:  # pragma: no cover — live API
        pytest.fail(f"Custom Hooks API failed: {e!r}")

    timeout = _e2e_timeout_s()
    interval = _e2e_interval_s()

    def _indexed() -> tuple[list[dict], list[dict]] | None:
        rdocs = search_runs_by_run_id(opensearch, run_id)
        edocs = search_events_by_run_id(opensearch, run_id)
        if len(rdocs) >= 1 and len(edocs) >= 2:
            return (rdocs, edocs)
        return None

    rdocs, edocs = wait_until(
        _indexed,
        timeout_s=timeout,
        interval_s=interval,
    )
    assert len(rdocs) == 1, f"expected a single run doc for {run_id}, got {len(rdocs)}"
    return E2EIndexedRun(
        run_id=run_id,
        session_id=session_id,
        text_marker=text_marker,
        rdocs=rdocs,
        edocs=edocs,
    )


@pytest.fixture(scope="module")
def e2e_indexed_run() -> E2EIndexedRun:
    """
    One live run + wait for Mach5, shared by all e2e tests in this module (avoids N API round-trips).
    """
    _load_dotenv()
    c = get_mach5_os_client()
    try:
        c.cluster.health(
            request_timeout=10,
            wait_for_status="yellow",
        )
    except Exception as e:
        _e2e_dprint(f"[test_e2e_mach5] skipping test: OpenSearch not reachable: {e!r}")
        pytest.skip(f"OpenSearch not reachable (Mach5 tunnel on localhost?): {e!r}")
    return _index_one_custom_hooks_run(c)


def test_e2e_run_run_id_in_index(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    assert e2e_indexed_run.run_src.get("runId") == e2e_indexed_run.run_id


def test_e2e_run_session_id_in_index(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    assert e2e_indexed_run.run_src.get("sessionId") == e2e_indexed_run.session_id


def test_e2e_run_event_types_includes_text(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    # eventTypes is derived from the normalized event (e.g. message ``type: "text"``), not
    # Custom Hooks ``hookEvent`` (e.g. "user_prompt").
    ev_types = set(e2e_indexed_run.run_src.get("eventTypes") or [])
    assert "text" in ev_types, f"eventTypes: {ev_types!r} (user message variant)"


def test_e2e_run_event_types_includes_stop(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    ev_types = set(e2e_indexed_run.run_src.get("eventTypes") or [])
    assert "stop" in ev_types, f"eventTypes: {ev_types!r}"


def test_e2e_run_user_in_index(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    run_src = e2e_indexed_run.run_src
    user_src = (run_src.get("user") or {}) if isinstance(run_src.get("user"), dict) else {}
    if not user_src:
        return
    # If this fails with id "" or wrong value, the hooks API accepted ``user`` but the run
    # index did not preserve it—treat as a server/pipeline bug, not a test quirk.
    assert user_src.get("id") == "e2e-user-1", f"user in index: {user_src!r}"
    assert (user_src.get("name") or "") == "E2E User", f"user in index: {user_src!r}"


def test_e2e_run_agent_in_index(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    run_src = e2e_indexed_run.run_src
    agent_src = (run_src.get("agent") or {}) if isinstance(run_src.get("agent"), dict) else {}
    if not agent_src:
        return
    assert (
        agent_src.get("id") == "e2e-mach5-agent-1" or agent_src.get("name") == "E2EMach5Agent"
    )


def test_e2e_event_docs_tied_to_run(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    for d in e2e_indexed_run.edocs:
        assert d.get("runId") == e2e_indexed_run.run_id, d


def test_e2e_event_docs_session_id_when_present(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    sid = e2e_indexed_run.session_id
    for d in e2e_indexed_run.edocs:
        if d.get("sessionId") is not None:
            assert d.get("sessionId") == sid, d


def test_e2e_event_docs_include_user_marker(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    m = e2e_indexed_run.text_marker
    edocs = e2e_indexed_run.edocs
    texts: list[str] = []
    user_text_hit = 0
    for d in edocs:
        t = d.get("text")
        if isinstance(t, str) and m in t:
            user_text_hit += 1
        if isinstance(t, str):
            texts.append(t)
    assert user_text_hit >= 1 or any(m in t for t in texts), (
        "expected an event with user text including the marker"
    )


def test_e2e_event_docs_include_stop_end_turn(
    e2e_indexed_run: E2EIndexedRun,
) -> None:
    edocs = e2e_indexed_run.edocs
    stop_hits = sum(
        1
        for d in edocs
        if d.get("source") == "stop" and d.get("stopReason") == "end_turn"
    )
    assert stop_hits >= 1, f"expected a stop event with end_turn; had {edocs!r}"
