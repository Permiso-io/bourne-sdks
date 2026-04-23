# permiso-custom-hooks-sdk

Python SDK for the [Permiso](https://permiso.io) Custom Hooks API. Send hook events from your application with automatic run handling: a `run_id` is generated when the client is constructed and sent on every request so events are correlated in the Agent Transaction Dashboard. Call `end_run()` to close out a run and rotate to a fresh `run_id` after a successful stop request.

## Install

```bash
pip install permiso-custom-hooks-sdk
```

## Quick start

```python
from permiso_custom_hooks import PermisoCustomHooksClient, PermisoCustomHooksConfig

config = PermisoCustomHooksConfig(api_key="your-api-secret")
client = PermisoCustomHooksClient(config)

print(client.get_run_id())  # run_id generated in the constructor

client.send_event("user_prompt", {"source": "user", "type": "text", "text": "Hello World"})

# Close out this run: sends a "stop" event, then rotates to a new run_id after success
client.end_run()

# Subsequent calls use the new run_id automatically
client.send_event(
    "web_fetch",
    {
        "source": "agent",
        "type": "tool_use",
        "name": "WebFetch",
        "toolUseId": "toolu_01abc",
        "input": {"url": "https://example.com"},
    },
)
```

### Sub-agents (parent and child runs)

```python
from permiso_custom_hooks import (
    PermisoAgentContext,
    PermisoCustomHooksClient,
    PermisoCustomHooksConfig,
)

parent = PermisoCustomHooksClient(PermisoCustomHooksConfig(api_key="your-api-secret"))
parent.send_event("user_prompt", {"source": "user", "type": "text", "text": "Hello"})
parent_run_id = parent.get_run_id()

sub = PermisoCustomHooksClient(
    PermisoCustomHooksConfig(
        api_key="your-api-secret",
        parent_run_id=parent_run_id,
        agent=PermisoAgentContext(name="ResearchSubAgent", id="sub-1"),
    )
)
sub.send_event("user_prompt", {"source": "user", "type": "text", "text": "Dig into details"})
```

## Request body shape

Every request POSTs to `{base_url}/hooks` with a JSON body shaped like this:

```json
{
  "hookEvent": "my_custom_event",
  "runId": "b1f0c3d4-....-uuid",
  "parentRunId": "optional-parent-run-uuid",
  "bourneVersion": "v2",
  "sessionId": "optional-if-set",
  "user": { "email": "jane@example.com", "id": "user-123", "name": "Jane" },
  "agent": {
    "systemPrompt": "optional-system-instructions",
    "name": "optional-agent-name",
    "id": "optional-custom-agent-id"
  },
  "event": { }
}
```

- `hookEvent` — the event name passed to `send_event`.
- `runId` — the current run ID, at the top level of the body.
- `parentRunId` — *(optional)* included when the client is configured with `parent_run_id` (same level as `runId`).
- `bourneVersion` — always `"v2"`; set by the SDK on every request.
- `sessionId` — *(optional)* included only if configured via the `session_id` option or `set_session_id`.
- `user` — *(optional)* end-user metadata; any subset of `email`, `id`, and `name`.
- `agent` — *(optional)* included when at least one of `systemPrompt`, `name`, or `id` is set; sent on **every** event (no separate `system_prompt` hook).
- `event` — the payload for this hook; see [Event payload (`event`)](#event-payload-event) below. When you omit `data` in `send_event`, the SDK sends `"event": {}`.

### Event payload (`event`)

The backend expects `event` to match **one** of the shapes below. For `source` `"user"` and `"agent"`, `type` selects the variant. For `source` `"stop"`, there is no `type` field.

On every variant, these fields are optional unless noted otherwise:

| Field | Description |
|-------|-------------|
| `eventId` | Stable id for this event (string). |
| `timestamp` | Epoch milliseconds (number) or ISO-8601 string. |

**Blob objects** (for `image` / `document` events):

| Field | Required | Description |
|-------|----------|-------------|
| `source` | yes | Origin label for the blob (string). |
| `data` | yes | Payload (e.g. base64). |
| `mediaType` | no | MIME type (string). |

**Agent-only optional fields** (allowed only when `source` is `"agent"`; omit on `source` `"user"`):

`model` (string), `temperature`, `maxTokens`, `topP`, `topK` (numbers) — all optional.

#### `source: "user"` (content)

| `type` | Required fields | Optional fields |
|--------|-----------------|-----------------|
| `"text"` | `text` | — |
| `"thinking"` | `thinking` | `thinkingBudget`, `signature` |
| `"tool_use"` | `name`, `toolUseId` | `input` (any JSON) |
| `"tool_result"` | `toolUseId` | `content`, `isError` |
| `"image"` | `image` (blob) | — |
| `"document"` | `document` (blob) | — |

#### `source: "agent"` (content)

Same rows as for `"user"`, plus the **agent-only optional fields** above on the same dict.

#### `source: "stop"` (run end)

No `type` property.

| Field | Required | Description |
|-------|----------|-------------|
| `source` | yes | Must be `"stop"`. |
| `stopReason` | no | One of: `"end_turn"`, `"max_tokens"`, `"stop_sequence"`, `"tool_use"`, `"content_filter"`. The client's `end_run(stop_reason=...)` defaults to `"end_turn"`. |
| `usage` | no | Token usage object (see below). |

**`usage`** when present:

```json
{
  "inputTokens": 0,
  "outputTokens": 0,
  "totalTokens": 0,
  "cacheReadTokens": 0,
  "cacheWriteTokens": 0,
  "cost": {
    "inputTokensCost": 0,
    "outputTokensCost": 0,
    "cacheReadTokensCost": 0,
    "cacheWriteTokensCost": 0,
    "currency": "USD"
  }
}
```

`cacheReadTokens`, `cacheWriteTokens`, and `cost` are optional; when `cost` is set, all of its fields are required as shown.

Do not send properties that are not listed for a variant if your integration is validated strictly (unknown keys may be rejected).

## Configuration

| Option      | Description |
|-------------|-------------|
| `api_key`   | Your Permiso agent API secret (from the A2M Keys tab in the dashboard). |
| `base_url`  | *(Optional.)* Base URL of the Permiso API (without `/hooks`). The client POSTs to `{base_url}/hooks`. Defaults to `https://alb.permiso.io`. |
| `parent_run_id` | *(Optional.)* Parent run UUID. Sent as top-level `parentRunId` on every request next to `runId` (e.g. sub-agents). |
| `agent` | *(Optional.)* `PermisoAgentContext` with optional `system_prompt`, `name`, and `id` (agent id, not end-user id). Merged with `system_prompt` when that field is not `None`. |
| `system_prompt` | *(Optional.)* After `agent` is applied, sets or overrides `agent.systemPrompt` on each request. |
| `session_id` | *(Optional.)* Session identifier. When set, it is attached as a top-level `sessionId` field on every request. |
| `user` | *(Optional.)* `PermisoUser` instance (fields: `email`, `id`, `name`) attached as a top-level `user` object on every request. |
| `raise_on_error` | *(Optional.)* Defaults to `False`. When `False`, `send_event` and `end_run` return `{}` on failure instead of raising; a failed `end_run` does not rotate `run_id`. When `True`, failures raise `PermisoCustomHooksError`. |

`system_prompt`, `session_id`, `user`, and agent fields can be updated after construction via `set_system_prompt`, `set_session_id`, `set_user`, and `set_agent`.

## Run lifecycle

1. **Construction** — A `run_id` (UUID) is generated in the constructor. Access it via `get_run_id()`.
2. **Sending events** — Every call to `send_event(...)` includes the current `run_id` at the top level of the body, so all events are tied to the same run.
3. **Ending a run** — Call `end_run()` to send a `stop` event for the current run. After the request **succeeds**, the client rotates to a new `run_id`. If the stop request fails and `raise_on_error` is `False` (the default), `end_run` returns `{}` and keeps the same `run_id`.

Run state is kept in memory only. If your process restarts, a new `run_id` is generated automatically when the next client is constructed.

## API

### `PermisoCustomHooksClient`

- **`__init__(config: PermisoCustomHooksConfig)`** — Creates a client from `api_key` and optional `base_url`, `parent_run_id`, `agent`, `system_prompt`, `session_id`, `user`, and `raise_on_error`. Generates an initial `run_id`.
- **`send_event(event_name: str, data: dict | None = None) -> dict`** — Sends a hook event. POSTs JSON including `hookEvent`, `runId`, `event`, `bourneVersion`, and when configured `parentRunId`, `sessionId`, `user`, and `agent`. On success returns the API response dict. When `raise_on_error` is `False`, failures return `{}` instead of raising.
- **`end_run(stop_reason: str = "end_turn") -> dict`** — Sends a `stop` hook with `event` `{"source": "stop", "stopReason": <stop_reason>}`, then rotates to a new `run_id` after a **successful** request. When `raise_on_error` is `False`, a failed stop returns `{}` and does not rotate `run_id`.
- **`get_run_id() -> str`** — Returns the current run ID (useful for logging, correlating logs, or passing as `parent_run_id` for a child client).
- **`set_system_prompt(prompt: str | None) -> None`** — Sets or clears the system prompt in the top-level `agent` object on every subsequent request.
- **`set_agent(*, system_prompt=..., name=..., id=...)`** — Merges agent fields; omit a keyword to leave that field unchanged, or pass `None` to clear it from the outbound `agent` payload. (Uses keyword-only arguments.)
- **`set_session_id(session_id: str | None) -> None`** — Sets (or clears) the session id attached as a top-level `sessionId` on every subsequent request.
- **`set_user(user: PermisoUser) -> None`** — Merges partial end-user metadata into the client's user state.

### `PermisoUser`

Dataclass describing optional user metadata: `email`, `id`, `name` (all `str | None`). Instances are passed to the `user` config option and to `set_user`.

### `PermisoAgentContext`

Dataclass with optional `system_prompt`, `name`, and `id` (agent identity; JSON keys are camelCase: `systemPrompt`, `name`, `id`). Used for the `agent` config option and merged with top-level `system_prompt` on construction.

### `PermisoCustomHooksError`

Raised when `raise_on_error` is `True` and the API returns a non-2xx or the request fails. Attributes:

- `message` — Error message.
- `status` — HTTP status code (optional).
- `body` — Response body (optional).

When `raise_on_error` is `True`, the client does not rotate its `run_id` after a failed `send_event` or failed `end_run`, so you can retry the same run. When `raise_on_error` is `False`, failures return `{}` and `run_id` is unchanged except after a successful `end_run`.

## Examples

Smoke-test against the API. Put `PERMISO_API_KEY=...` in a `.env` file at `custom-hooks-sdk-py/.env`, the repository root, or your current working directory (first file found is used). If `python-dotenv` is installed it is used; otherwise the script parses simple `KEY=VALUE` lines without extra dependencies.

```bash
cd custom-hooks-sdk-py
# optional: pip install python-dotenv
# Add PERMISO_API_KEY=... to .env
python examples/send_test_event.py
```

## Publishing

This package can be published to PyPI (public) or a private index. If using a private index, configure pip (e.g. `pip.conf` or `--index-url`) and authentication as needed for your organization.

## Requirements

- **Python** >= 3.9
- No runtime dependencies for the SDK (uses standard library `urllib`, `json`, and `uuid`).
- The example script can use **python-dotenv** when installed; otherwise it reads `.env` with a small stdlib parser.
