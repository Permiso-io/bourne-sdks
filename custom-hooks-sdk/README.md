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

await client.sendEvent("user_prompt", { source: "user", type: "text", text: "Hello World" });

// Close out this run: sends a "stop" event, then rotates to a new runId
await client.endRun();

// Subsequent calls use the new runId automatically
await client.sendEvent("web_fetch", {
  source: "agent",
  type: "tool_use",
  name: "WebFetch",
  toolUseId: "toolu_01abc",
  input: { url: "https://example.com" },
});
```

### Sub-agents (parent and child runs)

To correlate a child run with a parent run on the backend, read the parent’s `runId` and pass it as `parentRunId` when constructing the child client:

```typescript
const parent = new PermisoCustomHooksClient({ apiKey });
await parent.sendEvent("user_prompt", { source: "user", type: "text", text: "Hello" });
const parentRunId = parent.getRunId();

const sub = new PermisoCustomHooksClient({
  apiKey,
  parentRunId,
  agent: { name: "ResearchSubAgent", id: "sub-1" },
});
await sub.sendEvent("user_prompt", { source: "user", type: "text", text: "Dig into details" });
```

## Request body shape

Every request posts to `{baseUrl}/hooks` with a JSON body shaped like this:

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

- `hookEvent` — the event name passed to `sendEvent`.
- `runId` — the current run ID, at the top level of the body.
- `parentRunId` — *(optional)* included when the client is constructed with `parentRunId` (same level as `runId`) so the backend can link this run to a parent run.
- `bourneVersion` — always `"v2"`; set by the SDK on every request.
- `sessionId` — *(optional)* included only if configured via the `sessionId` option or `setSessionId`.
- `user` — *(optional)* included only if configured via the `user` option or `setUser`; contains any subset of `email`, `id`, and `name` (end-user metadata).
- `agent` — *(optional)* included when at least one of `systemPrompt`, `name`, or `id` is set; sent on **every** event for the current agent state (no separate `system_prompt` hook).
- `event` — the payload for this hook; see [Event payload (`event`)](#event-payload-event) below. When you omit `data` in `sendEvent`, the SDK sends `"event": {}`.

### Event payload (`event`)

The backend expects `event` to match **one** of the shapes below. For `source: "user"` and `source: "agent"`, `type` selects the variant. For `source: "stop"`, there is no `type` field.

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

**Agent-only optional fields** (allowed only when `source` is `"agent"`; omit on `source: "user"`):

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

Same rows as for `"user"`, plus the **agent-only optional fields** above on the same object.

#### `source: "stop"` (run end)

No `type` property.

| Field | Required | Description |
|-------|----------|-------------|
| `source` | yes | Must be `"stop"`. |
| `stopReason` | no | One of: `"end_turn"`, `"max_tokens"`, `"stop_sequence"`, `"tool_use"`, `"content_filter"`. The TypeScript client’s `endRun(stopReason?)` defaults this to `"end_turn"`. |
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

| Option   | Description |
|----------|-------------|
| `apiKey`  | Your Permiso agent API secret (from the A2M Keys tab in the dashboard). |
| `baseUrl` | *(Optional.)* Base URL of the Permiso API (without `/hooks`). The client posts to `{baseUrl}/hooks`. Defaults to `https://alb.permiso.io`. |
| `parentRunId` | *(Optional.)* Parent run UUID. When set, sent at the top level on every request next to `runId` so the backend can attach this run as a child of the parent (e.g. sub-agents). |
| `agent` | *(Optional.)* Initial agent metadata: `{ systemPrompt?, name?, id? }`. Merged with top-level `systemPrompt` when provided (see below). |
| `systemPrompt` | *(Optional.)* System prompt at the top level of config. After `agent` is applied, sets or overrides `agent.systemPrompt` for requests. |
| `sessionId` | *(Optional.)* Session identifier. When set, it is attached as a top-level `sessionId` field on every request. |
| `user` | *(Optional.)* End-user metadata (`{ email?, id?, name? }`) attached as a top-level `user` object on every request. |
| `raiseOnError` | *(Optional.)* Defaults to `false`. When `false`, `sendEvent` and `endRun` never throw for HTTP errors, invalid JSON, or transport failures; they return `{}` instead. When `true`, failures throw `PermisoCustomHooksError`. If `endRun` fails while `raiseOnError` is `false`, the current `runId` is left unchanged (no rotation). |

`systemPrompt`, `sessionId`, `user`, and agent fields can be updated after construction via `setSystemPrompt`, `setAgent`, `setSessionId`, and `setUser`.

## Run lifecycle

1. **Construction** — A `runId` (UUID) is generated in the constructor. Access it via `getRunId()`.
2. **Sending events** — Every call to `sendEvent(...)` includes the current `runId` at the top level of the body, so all events are tied to the same run.
3. **Ending a run** — Call `endRun()` to send a `stop` event for the current run. After the request **succeeds**, the client rotates to a new `runId`, so any subsequent `sendEvent` calls start a fresh run. If the stop request fails and `raiseOnError` is `false` (the default), `endRun` returns `{}` and keeps the same `runId`.

Run state is kept in memory only. If your process restarts, a new `runId` is generated automatically when the next client is constructed.

## API

### `PermisoCustomHooksClient`

- **`constructor(config: PermisoCustomHooksConfig)`** — Creates a client with `apiKey` and optional `baseUrl` (defaults to `https://alb.permiso.io`). Also accepts optional `parentRunId`, `agent`, `systemPrompt`, `sessionId`, `user`, and `raiseOnError`. Generates an initial `runId`.
- **`sendEvent(eventName: string, data?: Record<string, unknown>): Promise<CustomHooksResponse>`** — Sends a hook event. Posts `{ hookEvent: eventName, runId, event: data ?? {}, bourneVersion: "v2" }` to `{baseUrl}/hooks`, with top-level `parentRunId`, `sessionId`, `user`, and `agent` included when configured. Returns the API response on success. When `raiseOnError` is `false` (default), failures return `{}` instead of throwing.
- **`endRun(stopReason?: string): Promise<CustomHooksResponse>`** — Sends a `stop` hook with `event` `{ source: "stop", stopReason }` (default `stopReason`: `"end_turn"`), then rotates to a new `runId` after a **successful** request. When `raiseOnError` is `false`, a failed stop returns `{}` and does not rotate `runId`.
- **`getRunId(): string`** — Returns the current run ID (useful for logging, debugging, correlating client-side logs with dashboard entries, or passing as `parentRunId` for a child client).
- **`setSystemPrompt(prompt: string | undefined): void`** — Sets (or clears) the system prompt included in the top-level `agent` object on every subsequent request.
- **`setAgent(agent: Partial<PermisoAgentContext>): void`** — Merges partial agent metadata (`systemPrompt`, `name`, `id`) into the client's agent state for subsequent requests.
- **`setSessionId(sessionId: string | undefined): void`** — Sets (or clears) the session id attached as a top-level `sessionId` on every subsequent request.
- **`setUser(user: PermisoUser): void`** — Merges partial end-user metadata (`email`, `id`, `name`) into the client's user state. Callers can set just one field without clobbering the others. The resulting object is attached as a top-level `user` on every subsequent request.

### `PermisoAgentContext`

Shape of the top-level `agent` field on requests: `{ systemPrompt?: string; name?: string; id?: string }`. The `id` here identifies the **agent** (or sub-agent), not the end user (`user.id`).

### `PermisoCustomHooksError`

Thrown when the API returns a non-2xx or the request fails. Properties:

- `message` — Error message.
- `status` — HTTP status code (if available).
- `body` — Response body (if available).

On error, the client does not rotate its `runId`, so you can retry the same run. This applies when `raiseOnError` is `true` (errors surface to your code). When `raiseOnError` is `false`, `sendEvent` returns `{}` on failure and likewise does not rotate `runId` except after a successful `endRun`.

## Publishing

This package is configured for the public npm registry (`registry.npmjs.org`) under the `@permiso-io` scope.

Release steps:

1. Ensure you are logged in to npm: `npm whoami` (or `npm login`).
2. Bump version in `package.json` (or run `npm version <patch|minor|major>`).
3. Publish from this directory: `npm publish --access public`.

## Requirements

- **Node.js** >= 18 (uses global `fetch` and `crypto.randomUUID`).
- **TypeScript** optional; types are included (`lib/index.d.ts`).
