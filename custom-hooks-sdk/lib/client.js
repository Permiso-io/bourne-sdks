"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PermisoCustomHooksClient = exports.PermisoCustomHooksError = void 0;
/**
 * Error thrown when the Custom Hooks API returns a non-2xx or the request fails.
 */
class PermisoCustomHooksError extends Error {
    constructor(message, status, body) {
        super(message);
        this.status = status;
        this.body = body;
        this.name = "PermisoCustomHooksError";
        Object.setPrototypeOf(this, PermisoCustomHooksError.prototype);
    }
}
exports.PermisoCustomHooksError = PermisoCustomHooksError;
const HOOK_SOURCE_HEADER = "custom";
/**
 * Client for the Permiso Custom Hooks API.
 * Manages session ID automatically: the first successful response that includes sessionId
 * is stored and sent as session_id on all subsequent requests.
 */
class PermisoCustomHooksClient {
    constructor(config) {
        const base = config.baseUrl.replace(/\/$/, "");
        this.baseUrl = base;
        this.apiKey = config.apiKey;
        this.sessionId = undefined;
    }
    /**
     * Returns the current session ID if one has been received from the server (after the first successful sendEvent).
     * Useful for debugging or for persisting the session across process restarts (out of scope for v1).
     */
    getSessionId() {
        return this.sessionId;
    }
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
    async sendEvent(eventName, data) {
        const body = {
            hook_event_name: eventName,
            hookEvent: eventName,
            ...data,
        };
        if (this.sessionId !== undefined) {
            body.session_id = this.sessionId;
        }
        const url = `${this.baseUrl}/hooks`;
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-api-key": this.apiKey,
                "X-Hook-Source": HOOK_SOURCE_HEADER,
            },
            body: JSON.stringify(body),
        });
        const rawBody = await response.text();
        if (!response.ok) {
            throw new PermisoCustomHooksError(`Custom Hooks API error: ${response.status} ${response.statusText}`, response.status, rawBody);
        }
        let parsed;
        try {
            parsed = rawBody ? JSON.parse(rawBody) : {};
        }
        catch {
            throw new PermisoCustomHooksError("Invalid JSON response from Custom Hooks API", response.status, rawBody);
        }
        if (parsed.sessionId !== undefined && parsed.sessionId !== "") {
            this.sessionId = parsed.sessionId;
        }
        return parsed;
    }
    /**
     * Sends a "stop" event to trigger server-side aggregation for the current session.
     * Convenience method that calls sendEvent("stop", {}).
     */
    async endSession() {
        return this.sendEvent("stop", {});
    }
}
exports.PermisoCustomHooksClient = PermisoCustomHooksClient;
