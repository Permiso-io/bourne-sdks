import type { PermisoCustomHooksConfig, CustomHooksResponse } from "./types";
/**
 * Error thrown when the Custom Hooks API returns a non-2xx or the request fails.
 */
export declare class PermisoCustomHooksError extends Error {
    readonly status?: number | undefined;
    readonly body?: string | undefined;
    constructor(message: string, status?: number | undefined, body?: string | undefined);
}
/**
 * Client for the Permiso Custom Hooks API.
 * Manages session ID automatically: the first successful response that includes sessionId
 * is stored and sent as session_id on all subsequent requests.
 */
export declare class PermisoCustomHooksClient {
    private readonly baseUrl;
    private readonly apiKey;
    private sessionId;
    constructor(config: PermisoCustomHooksConfig);
    /**
     * Returns the current session ID if one has been received from the server (after the first successful sendEvent).
     * Useful for debugging or for persisting the session across process restarts (out of scope for v1).
     */
    getSessionId(): string | undefined;
    /**
     * Sends a hook event to the Permiso Custom Hooks endpoint.
     * On the first call, no session_id is sent; the server returns sessionId in the response and the client stores it.
     * On subsequent calls, session_id is included in the body so events are correlated to the same session.
     *
     * @param eventName - Hook event name (e.g. "session_start", "my_custom_event"). Sent as hook_event_name and hookEvent.
     * @param data - Optional additional payload fields (merged into the request body).
     * @returns The API response. Includes sessionId on the first response.
     * @throws PermisoCustomHooksError on non-2xx or network failure (sessionId is not updated).
     */
    sendEvent(eventName: string, data?: Record<string, unknown>): Promise<CustomHooksResponse>;
    /**
     * Sends a "stop" event to trigger server-side aggregation for the current session.
     * Convenience method that calls sendEvent("stop", {}).
     */
    endSession(): Promise<CustomHooksResponse>;
}
