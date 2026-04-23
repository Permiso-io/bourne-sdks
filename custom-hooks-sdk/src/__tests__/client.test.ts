import { PermisoCustomHooksClient, PermisoCustomHooksError } from "../client";

const mockFetch = jest.fn();

beforeEach(() => {
  mockFetch.mockReset();
  (global as unknown as { fetch: typeof mockFetch }).fetch = mockFetch;
});

function okJson(obj: object) {
  return {
    ok: true,
    status: 200,
    text: () => Promise.resolve(JSON.stringify(obj)),
  };
}

describe("PermisoCustomHooksClient", () => {
  const baseUrl = "https://api.example.com";
  const apiKey = "test-api-key";

  describe("sendEvent", () => {
    it("posts hookEvent, runId, event, and bourneVersion", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      await client.sendEvent("session_start");

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      expect(options.method).toBe("POST");
      expect(options.headers["Content-Type"]).toBe("application/json");
      expect(options.headers["x-api-key"]).toBe(apiKey);
      expect(options.headers["X-Hook-Source"]).toBe("custom");

      const body = JSON.parse(options.body as string);
      expect(body.hookEvent).toBe("session_start");
      expect(body.runId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
      expect(body.event).toEqual({});
      expect(body.bourneVersion).toBe("v2");
      expect(body.agent).toBeUndefined();
      expect(body.parentRunId).toBeUndefined();
    });

    it("includes sessionId when set on client", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({
        baseUrl,
        apiKey,
        sessionId: "sess-456",
      });
      await client.sendEvent("my_event", { key: "value" });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);
      expect(body.sessionId).toBe("sess-456");
      expect(body.hookEvent).toBe("my_event");
      expect(body.event).toEqual({ key: "value" });
    });

    it("defaults baseUrl to https://alb.permiso.io when omitted", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({ apiKey });
      await client.sendEvent("event");

      expect(mockFetch).toHaveBeenCalledWith("https://alb.permiso.io/hooks", expect.any(Object));
    });

    it("uses baseUrl without trailing slash", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({ baseUrl: "https://api.example.com/", apiKey });
      await client.sendEvent("event");

      expect(mockFetch).toHaveBeenCalledWith("https://api.example.com/hooks", expect.any(Object));
    });

    it("sends systemPrompt inside agent with a single request (no system_prompt hook)", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({
        baseUrl,
        apiKey,
        systemPrompt: "Be helpful",
      });
      await client.sendEvent("user_prompt", {
        source: "user",
        type: "text",
        text: "Hi",
      });

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);
      expect(body.hookEvent).toBe("user_prompt");
      expect(body.agent).toEqual({ systemPrompt: "Be helpful" });
    });

    it("merges config.agent then applies top-level systemPrompt override", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({
        baseUrl,
        apiKey,
        agent: { name: "A", systemPrompt: "from-agent" },
        systemPrompt: "from-top",
      });
      await client.sendEvent("e1");

      const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);
      expect(body.agent).toEqual({
        name: "A",
        systemPrompt: "from-top",
      });
    });

    it("includes parentRunId at top level when configured", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({
        baseUrl,
        apiKey,
        parentRunId: "parent-uuid-1",
      });
      await client.sendEvent("x");

      const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);
      expect(body.parentRunId).toBe("parent-uuid-1");
      expect(body.runId).not.toBe("parent-uuid-1");
    });

    it("reflects setAgent on subsequent requests", async () => {
      mockFetch.mockResolvedValueOnce(okJson({})).mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      await client.sendEvent("a");
      client.setAgent({ name: "Sub", id: "sub-9" });
      await client.sendEvent("b");

      const first = JSON.parse(mockFetch.mock.calls[0][1].body as string);
      expect(first.agent).toBeUndefined();

      const second = JSON.parse(mockFetch.mock.calls[1][1].body as string);
      expect(second.agent).toEqual({ name: "Sub", id: "sub-9" });
    });

    it("updates agent systemPrompt via setSystemPrompt on next send", async () => {
      mockFetch.mockResolvedValueOnce(okJson({})).mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({
        baseUrl,
        apiKey,
        systemPrompt: "one",
      });
      await client.sendEvent("e1");
      client.setSystemPrompt("two");
      await client.sendEvent("e2");

      expect(JSON.parse(mockFetch.mock.calls[0][1].body as string).agent).toEqual({
        systemPrompt: "one",
      });
      expect(JSON.parse(mockFetch.mock.calls[1][1].body as string).agent).toEqual({
        systemPrompt: "two",
      });
    });

    it("returns {} on non-2xx when raiseOnError is false (default)", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: () => Promise.resolve(JSON.stringify({ error: "Invalid API key" })),
      });

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      const result = await client.sendEvent("event");

      expect(result).toEqual({});
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("throws PermisoCustomHooksError on non-2xx when raiseOnError is true", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: () => Promise.resolve(JSON.stringify({ error: "Invalid API key" })),
      });

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey, raiseOnError: true });
      const promise = client.sendEvent("event");
      await expect(promise).rejects.toThrow(PermisoCustomHooksError);
      const err = (await promise.catch((e: unknown) => e)) as PermisoCustomHooksError;
      expect(err).toMatchObject({
        status: 401,
        body: expect.stringContaining("Invalid API key"),
      });
    });

    it("returns {} when fetch rejects and raiseOnError is false", async () => {
      mockFetch.mockRejectedValueOnce(new Error("network down"));

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      const result = await client.sendEvent("event");

      expect(result).toEqual({});
    });

    it("throws PermisoCustomHooksError when fetch rejects and raiseOnError is true", async () => {
      mockFetch.mockRejectedValueOnce(new Error("network down"));

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey, raiseOnError: true });
      await expect(client.sendEvent("event")).rejects.toThrow(PermisoCustomHooksError);
    });
  });

  describe("endRun", () => {
    it("sends stop event and rotates runId", async () => {
      mockFetch.mockResolvedValueOnce(okJson({}));

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      const before = client.getRunId();
      await client.endRun();
      const after = client.getRunId();

      expect(before).not.toBe(after);
      const body = JSON.parse(mockFetch.mock.calls[0][1].body as string);
      expect(body.hookEvent).toBe("stop");
      expect(body.event).toMatchObject({ source: "stop", stopReason: "end_turn" });
    });

    it("does not rotate runId when stop fails and raiseOnError is false", async () => {
      mockFetch.mockRejectedValueOnce(new Error("network down"));

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      const before = client.getRunId();
      const result = await client.endRun();
      const after = client.getRunId();

      expect(result).toEqual({});
      expect(before).toBe(after);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("throws and does not rotate runId when stop fails and raiseOnError is true", async () => {
      mockFetch.mockRejectedValueOnce(new Error("network down"));

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey, raiseOnError: true });
      const before = client.getRunId();
      await expect(client.endRun()).rejects.toThrow(PermisoCustomHooksError);
      expect(client.getRunId()).toBe(before);
    });
  });
});
