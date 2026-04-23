"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PermisoCustomHooksClient = exports.PermisoCustomHooksError = void 0;
const crypto_1 = require("crypto");
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
const BOURNE_VERSION = "v2";
/** Production Permiso API base URL (no trailing slash). Used when `baseUrl` is omitted from config. */
const DEFAULT_CUSTOM_HOOKS_BASE_URL = "https://alb.permiso.io";
function initialAgentState(config) {
    const fromAgent = config.agent ? { ...config.agent } : {};
    return {
        ...fromAgent,
        ...(config.systemPrompt !== undefined ? { systemPrompt: config.systemPrompt } : {}),
    };
}
/**
 * Client for the Permiso Custom Hooks API.
 * Manages a run ID automatically: the constructor generates an initial runId that is
 * sent on every request. Call `endRun()` to send a stop event and rotate to a new runId
 * for any subsequent calls.
 */
class PermisoCustomHooksClient {
    constructor(config) {
        const base = (config.baseUrl ?? DEFAULT_CUSTOM_HOOKS_BASE_URL).replace(/\/$/, "");
        this.baseUrl = base;
        this.apiKey = config.apiKey;
        this.parentRunId = config.parentRunId;
        this.runId = (0, crypto_1.randomUUID)();
        this.agent = initialAgentState(config);
        this.sessionId = config.sessionId;
        this.user = config.user ? { ...config.user } : undefined;
    }
    /**
     * Returns the current run ID. A new run ID is generated in the constructor and after every call to `endRun`.
     */
    getRunId() {
        return this.runId;
    }
    /**
     * Sets (or clears) the system prompt used in the top-level `agent` object on every request.
     */
    setSystemPrompt(prompt) {
        this.agent = { ...this.agent, systemPrompt: prompt };
    }
    /**
     * Merges partial agent metadata (`systemPrompt`, `name`, `id`) into the client's agent state.
     * The resulting object is attached as a top-level `agent` on every subsequent request when
     * at least one field is set.
     */
    setAgent(agent) {
        this.agent = { ...this.agent, ...agent };
    }
    /**
     * Sets (or clears) the session ID. When set, it is attached as a top-level
     * `sessionId` field on every subsequent request.
     */
    setSessionId(sessionId) {
        this.sessionId = sessionId;
    }
    /**
     * Merges partial user metadata into the client's user state. Callers can set
     * just one of `email`, `id`, or `name` without clobbering the others. The
     * resulting user object is attached as a top-level `user` field on every
     * subsequent request.
     */
    setUser(user) {
        this.user = { ...(this.user ?? {}), ...user };
    }
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
    async sendEvent(eventName, data) {
        const body = {
            hookEvent: eventName,
            runId: this.runId,
            event: { ...(data ?? {}) },
            bourneVersion: BOURNE_VERSION,
        };
        if (this.parentRunId !== undefined) {
            body.parentRunId = this.parentRunId;
        }
        if (this.sessionId !== undefined) {
            body.sessionId = this.sessionId;
        }
        if (this.user && this.hasUserField(this.user)) {
            body.user = { ...this.user };
        }
        const agentPayload = this.buildAgentPayload();
        if (agentPayload) {
            body.agent = agentPayload;
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
            throw new PermisoCustomHooksError(`API error: ${response.status} ${response.statusText}`, response.status, rawBody);
        }
        let parsed;
        try {
            parsed = rawBody ? JSON.parse(rawBody) : {};
        }
        catch {
            throw new PermisoCustomHooksError("Invalid JSON response from Custom Hooks API", response.status, rawBody);
        }
        return parsed;
    }
    /**
     * Sends a "stop" event for the current run, then rotates to a fresh runId so any
     * subsequent calls to `sendEvent` start a new run.
     */
    async endRun(stopReason = "end_turn") {
        const response = await this.sendEvent("stop", { source: "stop", stopReason });
        this.runId = (0, crypto_1.randomUUID)();
        return response;
    }
    buildAgentPayload() {
        const { systemPrompt, name, id } = this.agent;
        const out = {};
        if (systemPrompt !== undefined) {
            out.systemPrompt = systemPrompt;
        }
        if (name !== undefined) {
            out.name = name;
        }
        if (id !== undefined) {
            out.id = id;
        }
        return this.hasAgentField(out) ? out : undefined;
    }
    hasAgentField(agent) {
        return (agent.systemPrompt !== undefined ||
            agent.name !== undefined ||
            agent.id !== undefined);
    }
    hasUserField(user) {
        return user.email !== undefined || user.id !== undefined || user.name !== undefined;
    }
}
exports.PermisoCustomHooksClient = PermisoCustomHooksClient;
