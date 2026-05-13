# News agent + Custom Hooks SDK — implementation friction

Observed wiring `permiso_custom_hooks` into mock agent scenarios under `test_sdk_py/agents/` (v2 payloads, default `raise_on_error=False`).

- **`.env` discovery lives in the SDK example, not the package**: README documents loading order under `custom-hooks-sdk-py/`; the demo app had to re-implement the same path walk (or users rely on exporting vars only).
- **`hookEvent` vs `event.type`**: Quick start mixes a string like `"web_fetch"` with payload `type: "tool_use"`; it is easy to assume `send_event` takes a single enum instead of `(hook_name, validated_event_dict)`.
- **`tool_use` / `tool_result` pairing**: README quick start once omitted `toolUseId`; integration must invent stable ids and keep them aligned across result rows (same note as `DEVELOPER_ONBOARDING.md`).
- **`tool_result.content`**: Still non-obvious that structured tool output should go in `content` (often as JSON text); nothing in the types forces that convention.
- **`end_run()` lifecycle**: Easy to forget on early `sys.exit` paths; runs stay “open” in the dashboard until `stop` is sent; wrapping the whole agent turn in `try/finally` is necessary, not shown in the minimal snippet.
- **`raise_on_error=False` default**: Failed POSTs return `{}` with no exception; without checking responses or flipping the flag, integrations silently lose telemetry.
- **Agent identity vs run correlation**: `PermisoAgentContext.id` is the stable agent deployment id (distinct from `name`); correlating one CLI invocation needs `session_id` and/or `run_id`, not a per-run value in `agent.id` — easy to conflate until you read the config table, not quick start alone.
- **Thinking vs stderr**: Simulated agent lines stay on stderr; mapping them to hooks means duplicating strings or refactoring emitters (SDK does not bridge logging).
