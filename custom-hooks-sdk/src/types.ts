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
   * Optional system prompt. When set, the SDK emits a dedicated `system_prompt` event
   * before the first event of each run (including after `endRun` rotates the runId).
   */
  systemPrompt?: string;
  /** Optional session id. When set, it is attached as a top-level `sessionId` on every request. */
  sessionId?: string;
  /** Optional user metadata attached as a top-level `user` object on every request. */
  user?: PermisoUser;
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
