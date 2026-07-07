/**
 * Typed hook event payloads for the `event` field on Custom Hooks requests.
 * Matches the Bourne v2 content-block schema (see package README).
 */
/** Optional fields present on any content event variant. */
export interface PermisoHookEventBase {
    /** Stable id for this event. */
    eventId?: string;
    /** Epoch milliseconds or ISO-8601 string. */
    timestamp?: number | string;
}
/** Agent-only optional fields (omit when `source` is `"user"`). */
export interface PermisoAgentEventFields {
    model?: string;
    temperature?: number;
    maxTokens?: number;
    topP?: number;
    topK?: number;
}
/** User-originated `tool_result` content block. */
export interface PermisoUserToolResultEvent extends PermisoHookEventBase {
    source: "user";
    type: "tool_result";
    toolUseId: string;
    /** Tool name (optional; used for dashboard display). */
    name?: string;
    content?: string;
    isError?: boolean;
}
/** Agent-originated `tool_result` content block. */
export interface PermisoAgentToolResultEvent extends PermisoHookEventBase, PermisoAgentEventFields {
    source: "agent";
    type: "tool_result";
    toolUseId: string;
    /** Tool name (optional; used for dashboard display). */
    name?: string;
    content?: string;
    isError?: boolean;
}
/** `tool_result` event payload (`source: "user"` or `"agent"`). */
export type PermisoToolResultEvent = PermisoUserToolResultEvent | PermisoAgentToolResultEvent;
/**
 * Structured hook event payloads supported by the SDK.
 * Custom or forward-compatible fields may still be sent via `Record<string, unknown>`.
 */
export type PermisoHookEventPayload = PermisoToolResultEvent;
