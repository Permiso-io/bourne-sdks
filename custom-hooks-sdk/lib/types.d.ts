/**
 * Configuration for the Permiso Custom Hooks client.
 */
export interface PermisoCustomHooksConfig {
    /** Base URL of the Permiso API (e.g. https://alb.permiso.io). The client will POST to {baseUrl}/hooks */
    baseUrl: string;
    /** API key (secret) for authentication. Use the secret from your Permiso agent (A2M Keys). */
    apiKey: string;
}
/**
 * Response shape from the Custom Hooks API.
 * - First request: server returns sessionId so the client can send it on subsequent requests.
 * - Optional: continue, permission, user_message, agent_message for allow/deny flows.
 */
export interface CustomHooksResponse {
    /** Present on first response; send as session_id or sessionId in subsequent request bodies */
    sessionId?: string;
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
