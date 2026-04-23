/**
 * User metadata attached to each request when set via `setUser` or the `user` config option.
 * All fields are optional; `setUser` merges partial updates into the current value.
 */
export interface PermisoUser {
  /** Email address of the end user. */
  email?: string;
  /** Stable identifier of the end user. */
  id?: string;
  /** Display name of the end user. */
  name?: string;
}

/**
 * Agent metadata attached to each request when any field is set, via `agent` / `setAgent` /
 * `setSystemPrompt` or the top-level `systemPrompt` config option.
 */
export interface PermisoAgentContext {
  /** System instructions for the agent. */
  systemPrompt?: string;
  /** Display or logical name of the agent. */
  name?: string;
  /** Custom stable identifier for this agent (distinct from end-user `user.id`). */
  id?: string;
}

/**
 * Configuration for the Permiso Custom Hooks client.
 */
export interface PermisoCustomHooksConfig {
  /**
   * Base URL of the Permiso API (without `/hooks`). The client POSTs to `{baseUrl}/hooks`.
   * Defaults to `https://alb.permiso.io` when omitted.
   */
  baseUrl?: string;
  /** API key (secret) for authentication. Use the secret from your Permiso agent (A2M Keys). */
  apiKey: string;
  /**
   * Optional parent run ID. When set (e.g. for a sub-agent), it is sent at the top level
   * on every request next to `runId` so the backend can link child runs to a parent run.
   */
  parentRunId?: string;
  /**
   * Optional initial agent metadata (`systemPrompt`, `name`, `id`). Sent as a top-level
   * `agent` object on every request when at least one field is set. Merged with top-level
   * `systemPrompt` when that option is provided (see `systemPrompt`).
   */
  agent?: PermisoAgentContext;
  /**
   * Optional system prompt at the top level of config. Initializes or overrides
   * `agent.systemPrompt` after `agent` is applied (so existing callers can keep using this field).
   */
  systemPrompt?: string;
  /** Optional session id. When set, it is attached as a top-level `sessionId` on every request. */
  sessionId?: string;
  /** Optional user metadata attached as a top-level `user` object on every request. */
  user?: PermisoUser;
  /**
   * When `true`, `sendEvent` and `endRun` throw `PermisoCustomHooksError` on HTTP errors,
   * invalid JSON, or transport failures. When `false` (the default), those methods return `{}` instead
   * of throwing; `endRun` does not rotate `runId` if the stop request fails.
   */
  raiseOnError?: boolean;
}

/**
 * Response shape from the Custom Hooks API.
 * - Optional: continue, permission, user_message, agent_message for allow/deny flows.
 */
export interface CustomHooksResponse {
  /** For prompt-style events: whether to continue (e.g. allow the action) */
  continue?: boolean;
  /** For permission-style events: "allow" | "deny" */
  permission?: string;
  /** Message shown to the user when blocked */
  user_message?: string;
  /** Message shown to the agent when blocked */
  agent_message?: string;
  [key: string]: unknown;
}
