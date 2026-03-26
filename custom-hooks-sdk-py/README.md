# permiso-custom-hooks-sdk

Python SDK for the [Permiso](https://permiso.io) Custom Hooks API. Send hook events from your application with automatic run handling: a `run_id` is generated when the client is constructed and sent on every request so events are correlated in the Agent Transaction Dashboard. Call `end_run()` to close out a run and rotate to a fresh `run_id` for subsequent calls.

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

# Close out this run: sends a "stop" event, then rotates to a new run_id
client.end_run()

# Subsequent calls use the new run_id automatically
client.send_event(
    "web_fetch",
    {
        "source": "agent",
        "type": "tool_use",
        "name": "WebFetch",
        "input": "https://example.com",
    },
)
```

## Request body shape

Every request POSTs to `{base_url}/hooks` with a JSON body shaped like this:

```json
{
  "hookEvent": "my_custom_event",
  "runId": "b1f0c3d4-....-uuid",
  "sessionId": "optional-if-set",
  "user": { "email": "jane@example.com", "id": "user-123", "name": "Jane" },
  "event": {
    "source": "user|agent|stop",
    "type": "text|thinking|tool_use|tool_result|image|document"
  }
}
```

- `hookEvent` — the event name passed to `send_event`.
- `runId` — the current run ID, at the top level of the body.
- `sessionId` — *(optional)* included only if configured via the `session_id` option or `set_session_id`.
- `user` — *(optional)* included only if configured via the `user` option or `set_user`; contains any subset of `email`, `id`, and `name`.
- `event` — an object containing whatever `data` you passed to `send_event` (or `{}` if you didn't pass any).

## Configuration

| Option      | Description |
|-------------|-------------|
| `api_key`   | Your Permiso agent API secret (from the A2M Keys tab in the dashboard). |
| `base_url`  | *(Optional.)* Base URL of the Permiso API (without `/hooks`). The client POSTs to `{base_url}/hooks`. Defaults to `https://alb.permiso.io`. |
| `system_prompt` | *(Optional.)* System prompt for the agent. When set, the SDK emits a dedicated `system_prompt` event before the first event of each run (including after `end_run`). |
| `session_id` | *(Optional.)* Session identifier. When set, it is attached as a top-level `sessionId` field on every request. |
| `user` | *(Optional.)* `PermisoUser` instance (fields: `email`, `id`, `name`) attached as a top-level `user` object on every request. |

All three of `system_prompt`, `session_id`, and `user` can also be configured after construction via `set_system_prompt`, `set_session_id`, and `set_user`.

## Run lifecycle

1. **Construction** — A `run_id` (UUID) is generated in the constructor. Access it via `get_run_id()`.
2. **Sending events** — Every call to `send_event(...)` includes the current `run_id` at the top level of the body, so all events are tied to the same run.
3. **Ending a run** — Call `end_run()` to send a `stop` event for the current run. After the request completes, the client rotates to a new `run_id`, so any subsequent `send_event` calls start a fresh run.

Run state is kept in memory only. If your process restarts, a new `run_id` is generated automatically when the next client is constructed.

## API

### `PermisoCustomHooksClient`

- **`__init__(config: PermisoCustomHooksConfig)`** — Creates a client with `api_key` and optional `base_url` (defaults to `https://alb.permiso.io`). Also accepts optional `system_prompt`, `session_id`, and `user`. Generates an initial `run_id`.
- **`send_event(event_name: str, data: dict | None = None) -> dict`** — Sends a hook event. POSTs `{"hookEvent": event_name, "runId": <current>, "event": data or {}}` to `{base_url}/hooks`, with top-level `sessionId` and `user` included when configured. Returns the API response dict.
- **`end_run() -> dict`** — Sends a `stop` event for the current run, then rotates to a new `run_id` for subsequent calls. Also resets the per-run system-prompt flag so the prompt is re-emitted for the next run.
- **`get_run_id() -> str`** — Returns the current run ID (useful for logging, debugging, or correlating client-side logs with dashboard entries).
- **`set_system_prompt(prompt: str | None) -> None`** — Sets (or clears) the system prompt. When set, the SDK sends a dedicated `system_prompt` event before the first event of each run (payload: `{"source": "system", "type": "text", "text": <prompt>}`). If the first event of the current run has already been sent, the prompt is emitted before the first event of the next run.
- **`set_session_id(session_id: str | None) -> None`** — Sets (or clears) the session id attached as a top-level `sessionId` on every subsequent request.
- **`set_user(user: PermisoUser) -> None`** — Merges partial user metadata (`email`, `id`, `name`) into the client's user state. Callers can set just one field without clobbering the others. The resulting object is attached as a top-level `user` on every subsequent request.

### `PermisoUser`

Dataclass describing optional user metadata: `email`, `id`, `name` (all `str | None`). Instances are passed to the `user` config option and to `set_user`.

### `PermisoCustomHooksError`

Raised when the API returns a non-2xx or the request fails. Attributes:

- `message` — Error message.
- `status` — HTTP status code (optional).
- `body` — Response body (optional).

On error, the client does not rotate its `run_id`, so you can retry the same run.

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
