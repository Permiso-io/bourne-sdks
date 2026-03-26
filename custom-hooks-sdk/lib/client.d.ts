import type { PermisoCustomHooksConfig, CustomHooksResponse, PermisoUser } from "./types";
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
    private runId;
    private systemPrompt?;
    private sessionId?;
    private user?;
    private systemPromptSentForCurrentRun;
    constructor(config: PermisoCustomHooksConfig);
    /**
     * Returns the current run ID. A new run ID is generated in the constructor and after every call to `endRun`.
     */
    getRunId(): string;
    /**
     * Sets (or clears) the system prompt. When set, the SDK emits a dedicated
     * `system_prompt` event before the first event of each run. If the first event of
     * the current run has already been sent, the prompt will instead be emitted before
     * the first event of the next run (after `endRun`).
     */
    setSystemPrompt(prompt: string | undefined): void;
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
     * `sessionId` and `user` are also attached at the top level.
     *
     * If a system prompt is set and has not yet been emitted for the current run,
     * a `system_prompt` event is sent first.
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
    private hasUserField;
}
