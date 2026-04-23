import type { PermisoAgentContext, PermisoCustomHooksConfig, CustomHooksResponse, PermisoUser } from "./types";
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
 * Manages a run ID automatically: the constructor generates an initial runId that is
 * sent on every request. Call `endRun()` to send a stop event and rotate to a new runId
 * for any subsequent calls.
 */
export declare class PermisoCustomHooksClient {
    private readonly baseUrl;
    private readonly apiKey;
    private readonly parentRunId?;
    private runId;
    private agent;
    private sessionId?;
    private user?;
    constructor(config: PermisoCustomHooksConfig);
    /**
     * Returns the current run ID. A new run ID is generated in the constructor and after every call to `endRun`.
     */
    getRunId(): string;
    /**
     * Sets (or clears) the system prompt used in the top-level `agent` object on every request.
     */
    setSystemPrompt(prompt: string | undefined): void;
    /**
     * Merges partial agent metadata (`systemPrompt`, `name`, `id`) into the client's agent state.
     * The resulting object is attached as a top-level `agent` on every subsequent request when
     * at least one field is set.
     */
    setAgent(agent: Partial<PermisoAgentContext>): void;
    /**
     * Sets (or clears) the session ID. When set, it is attached as a top-level
     * `sessionId` field on every subsequent request.
     */
    setSessionId(sessionId: string | undefined): void;
    /**
     * Merges partial user metadata into the client's user state. Callers can set
     * just one of `email`, `id`, or `name` without clobbering the others. The
     * resulting user object is attached as a top-level `user` field on every
     * subsequent request.
     */
    setUser(user: PermisoUser): void;
    /**
     * Sends a hook event to the Permiso Custom Hooks endpoint.
     * The request body has the shape `{ hookEvent, runId, event, bourneVersion }`: `hookEvent` is the event
     * name, `runId` is the current run ID at the top level of the body, and `event` is an
     * object containing the optional payload fields from `data`. When configured,
     * `parentRunId`, `sessionId`, `user`, and `agent` are also attached at the top level.
     *
     * @param eventName - Hook event name (e.g. "session_start", "my_custom_event"). Sent as hookEvent.
     * @param data - Optional event payload fields. Sent as the `event` object on the request body.
     * @returns The API response.
     * @throws PermisoCustomHooksError on non-2xx or network failure.
     */
    sendEvent(eventName: string, data?: Record<string, unknown>): Promise<CustomHooksResponse>;
    /**
     * Sends a "stop" event for the current run, then rotates to a fresh runId so any
     * subsequent calls to `sendEvent` start a new run.
     */
    endRun(stopReason?: string): Promise<CustomHooksResponse>;
    private buildAgentPayload;
    private hasAgentField;
    private hasUserField;
}
