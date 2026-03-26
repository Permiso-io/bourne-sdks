# @permiso-io/custom-hooks-sdk

SDK for the [Permiso](https://permiso.io) Custom Hooks API. Send hook events from your application with automatic session handling: the first request receives a `sessionId` from the server, and the SDK sends it on all subsequent requests so events are correlated in the Agent Transaction Dashboard.

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
  baseUrl: "https://alb.permiso.io",  // Permiso API base (no trailing slash)
  apiKey: process.env.PERMISO_API_KEY!,
});

// First event: no session_id sent; server returns sessionId and the SDK stores it
const first = await client.sendEvent("session_start");
console.log(first.sessionId);  // present on first response

// Later events: session_id is sent automatically
await client.sendEvent("my_custom_event", { action: "did_something", count: 1 });

// Optional: send "stop" to trigger server-side aggregation for this session
await client.endSession();
```

## Configuration

| Option   | Description |
|----------|-------------|
| `baseUrl` | Base URL of the Permiso API (without `/hooks`). The client posts to `{baseUrl}/hooks`. |
| `apiKey`  | Your Permiso agent API secret (from the A2M Keys tab in the dashboard). |

### Environment URLs

| Environment | baseUrl |
|-------------|--------|
| Production  | `https://alb.permiso.io` |
| Staging     | `https://staging-alb.permiso.io` |
| Local       | `http://localhost:4007` (e.g. when running the hooks endpoint locally) |

## Session lifecycle

1. **First request** — You call `sendEvent(...)` without having received a session yet. The SDK does not send `session_id` in the body. The server creates a session and returns `sessionId` in the response. The SDK stores it.
2. **Subsequent requests** — The SDK includes `session_id` in every request body so all events are tied to the same session.
3. **Optional** — Call `endSession()` to send a `stop` event; the server will aggregate the session for the dashboard.

Session state is kept in memory only. If your process restarts, the next `sendEvent` will start a new session (no `session_id` sent until the server returns a new `sessionId`).

## API

### `PermisoCustomHooksClient`

- **`constructor(config: PermisoCustomHooksConfig)`** — Creates a client with `baseUrl` and `apiKey`.
- **`sendEvent(eventName: string, data?: Record<string, unknown>): Promise<CustomHooksResponse>`** — Sends a hook event. `eventName` is sent as `hook_event_name` and `hookEvent`; `data` is merged into the body. Returns the API response; on first success, the response includes `sessionId` and the client stores it for later calls.
- **`endSession(): Promise<CustomHooksResponse>`** — Sends a `stop` event to trigger aggregation.
- **`getSessionId(): string | undefined`** — Returns the current session ID if one has been received (useful for debugging or custom persistence).

### `PermisoCustomHooksError`

Thrown when the API returns a non-2xx or the request fails. Properties:

- `message` — Error message.
- `status` — HTTP status code (if available).
- `body` — Response body (if available).

On error, the client does not update its stored `sessionId`, so you can retry or start a new flow.

## Publishing

This package is configured for the public npm registry (`registry.npmjs.org`) under the `@permiso-io` scope.

Release steps:

1. Ensure you are logged in to npm: `npm whoami` (or `npm login`).
2. Bump version in `package.json` (or run `npm version <patch|minor|major>`).
3. Publish from this directory: `npm publish --access public`.

## Requirements

- **Node.js** >= 18 (uses global `fetch`).
- **TypeScript** optional; types are included (`lib/index.d.ts`).
