# @permiso-io/custom-hooks-sdk

SDK for the [Permiso](https://permiso.io) Custom Hooks API. Send hook events from your application with automatic run handling: the SDK generates a `runId` when the client is created and sends it on every request so events are correlated in the Agent Transaction Dashboard. Call `endRun()` to close out a run and rotate to a fresh `runId` for subsequent calls.

## Install

```bash
npm install @permiso-io/custom-hooks-sdk
```

Or with yarn / pnpm:

```bash
yarn add @permiso-io/custom-hooks-sdk
pnpm add @permiso-io/custom-hooks-sdk
```

No additional npm registry configuration is required for public installs.

## Quick start

```typescript
import { PermisoCustomHooksClient } from "@permiso-io/custom-hooks-sdk";

const client = new PermisoCustomHooksClient({
  apiKey: process.env.PERMISO_API_KEY!,
});

console.log(client.getRunId()); // runId generated in the constructor

await client.sendEvent("user_prompt", { source: "user", type:"text", text: "Hello World" });

// Close out this run: sends a "stop" event, then rotates to a new runId
await client.endRun();

// Subsequent calls use the new runId automatically
await client.sendEvent("web_fetch", { source: "agent", type: "tool_use", name: "WebFetch", input: "https://example.com" });
```

## Request body shape

Every request posts to `{baseUrl}/hooks` with a JSON body shaped like this:

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

- `hookEvent` — the event name passed to `sendEvent`.
- `runId` — the current run ID, at the top level of the body.
- `sessionId` — *(optional)* included only if configured via the `sessionId` option or `setSessionId`.
- `user` — *(optional)* included only if configured via the `user` option or `setUser`; contains any subset of `email`, `id`, and `name`.
- `event` — an object containing whatever `data` you passed to `sendEvent` (or `{}` if you didn't pass any).

## Configuration

| Option   | Description |
|----------|-------------|
| `apiKey`  | Your Permiso agent API secret (from the A2M Keys tab in the dashboard). |
| `baseUrl` | *(Optional.)* Base URL of the Permiso API (without `/hooks`). The client posts to `{baseUrl}/hooks`. Defaults to `https://alb.permiso.io`. |
| `systemPrompt` | *(Optional.)* System prompt for the agent. When set, the SDK emits a dedicated `system_prompt` event before the first event of each run (including after `endRun`). |
| `sessionId` | *(Optional.)* Session identifier. When set, it is attached as a top-level `sessionId` field on every request. |
| `user` | *(Optional.)* User metadata (`{ email?, id?, name? }`) attached as a top-level `user` object on every request. |

All three of `systemPrompt`, `sessionId`, and `user` can also be configured after construction via `setSystemPrompt`, `setSessionId`, and `setUser`.

## Run lifecycle

1. **Construction** — A `runId` (UUID) is generated in the constructor. Access it via `getRunId()`.
2. **Sending events** — Every call to `sendEvent(...)` includes the current `runId` at the top level of the body, so all events are tied to the same run.
3. **Ending a run** — Call `endRun()` to send a `stop` event for the current run. After the request completes, the client rotates to a new `runId`, so any subsequent `sendEvent` calls start a fresh run.

Run state is kept in memory only. If your process restarts, a new `runId` is generated automatically when the next client is constructed.

## API

### `PermisoCustomHooksClient`

- **`constructor(config: PermisoCustomHooksConfig)`** — Creates a client with `apiKey` and optional `baseUrl` (defaults to `https://alb.permiso.io`). Also accepts optional `systemPrompt`, `sessionId`, and `user`. Generates an initial `runId`.
- **`sendEvent(eventName: string, data?: Record<string, unknown>): Promise<CustomHooksResponse>`** — Sends a hook event. Posts `{ hookEvent: eventName, runId, event: data ?? {} }` to `{baseUrl}/hooks`, with top-level `sessionId` and `user` included when configured. Returns the API response.
- **`endRun(): Promise<CustomHooksResponse>`** — Sends a `stop` event for the current run, then rotates to a new `runId` for subsequent calls. Also resets the per-run system-prompt flag so the prompt is re-emitted for the next run.
- **`getRunId(): string`** — Returns the current run ID (useful for logging, debugging, or correlating client-side logs with dashboard entries).
- **`setSystemPrompt(prompt: string | undefined): void`** — Sets (or clears) the system prompt. When set, the SDK sends a dedicated `system_prompt` event before the first event of each run (payload: `{ source: "system", type: "text", text: <prompt> }`). If the first event of the current run has already been sent, the prompt is emitted before the first event of the next run.
- **`setSessionId(sessionId: string | undefined): void`** — Sets (or clears) the session id attached as a top-level `sessionId` on every subsequent request.
- **`setUser(user: PermisoUser): void`** — Merges partial user metadata (`email`, `id`, `name`) into the client's user state. Callers can set just one field without clobbering the others. The resulting object is attached as a top-level `user` on every subsequent request.

### `PermisoCustomHooksError`

Thrown when the API returns a non-2xx or the request fails. Properties:

- `message` — Error message.
- `status` — HTTP status code (if available).
- `body` — Response body (if available).

On error, the client does not rotate its `runId`, so you can retry the same run.

## Publishing

This package is configured for the public npm registry (`registry.npmjs.org`) under the `@permiso-io` scope.

Release steps:

1. Ensure you are logged in to npm: `npm whoami` (or `npm login`).
2. Bump version in `package.json` (or run `npm version <patch|minor|major>`).
3. Publish from this directory: `npm publish --access public`.

## Requirements

- **Node.js** >= 18 (uses global `fetch` and `crypto.randomUUID`).
- **TypeScript** optional; types are included (`lib/index.d.ts`).
