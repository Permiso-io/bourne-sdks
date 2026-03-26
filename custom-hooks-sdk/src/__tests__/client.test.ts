import { PermisoCustomHooksClient, PermisoCustomHooksError } from "../client";

const mockFetch = jest.fn();

beforeEach(() => {
  mockFetch.mockReset();
  (global as any).fetch = mockFetch;
});

describe("PermisoCustomHooksClient", () => {
  const baseUrl = "https://api.example.com";
  const apiKey = "test-api-key";

  describe("sendEvent", () => {
    it("sends first request without session_id and stores sessionId from response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve(JSON.stringify({ sessionId: "sess-123", continue: true })),
      });

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      const result = await client.sendEvent("session_start");

      expect(result.sessionId).toBe("sess-123");
      expect(result.continue).toBe(true);
      expect(client.getSessionId()).toBe("sess-123");

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toBe("https://api.example.com/hooks");
      expect(options.method).toBe("POST");
      expect(options.headers["Content-Type"]).toBe("application/json");
      expect(options.headers["x-api-key"]).toBe(apiKey);
      expect(options.headers["X-Hook-Source"]).toBe("custom");

      const body = JSON.parse(options.body);
      expect(body.hook_event_name).toBe("session_start");
      expect(body.hookEvent).toBe("session_start");
      expect(body.session_id).toBeUndefined();
    });

    it("sends subsequent requests with session_id", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          text: () => Promise.resolve(JSON.stringify({ sessionId: "sess-456", continue: true })),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          text: () => Promise.resolve(JSON.stringify({ permission: "allow" })),
        });

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      await client.sendEvent("session_start");
      await client.sendEvent("my_event", { key: "value" });

      expect(mockFetch).toHaveBeenCalledTimes(2);
      const secondCallBody = JSON.parse(mockFetch.mock.calls[1][1].body);
      expect(secondCallBody.session_id).toBe("sess-456");
      expect(secondCallBody.hook_event_name).toBe("my_event");
      expect(secondCallBody.key).toBe("value");
    });

    it("defaults baseUrl to https://alb.permiso.io when omitted", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve("{}"),
      });

      const client = new PermisoCustomHooksClient({ apiKey });
      await client.sendEvent("event");

      expect(mockFetch).toHaveBeenCalledWith(
        "https://alb.permiso.io/hooks",
        expect.any(Object),
      );
    });

    it("uses baseUrl without trailing slash", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve("{}"),
      });

      const client = new PermisoCustomHooksClient({ baseUrl: "https://api.example.com/", apiKey });
      await client.sendEvent("event");

      expect(mockFetch).toHaveBeenCalledWith(
        "https://api.example.com/hooks",
        expect.any(Object),
      );
    });

    it("throws PermisoCustomHooksError on non-2xx", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        text: () => Promise.resolve(JSON.stringify({ error: "Invalid API key" })),
      });

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      const promise = client.sendEvent("event");
      await expect(promise).rejects.toThrow(PermisoCustomHooksError);
      const err = await promise.catch((e: unknown) => e);
      expect(err).toMatchObject({
        status: 401,
        body: expect.stringContaining("Invalid API key"),
      });
      expect(client.getSessionId()).toBeUndefined();
    });

    it("does not update sessionId on error", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          text: () => Promise.resolve(JSON.stringify({ sessionId: "sess-1" })),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
          text: () => Promise.resolve(""),
        });

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      await client.sendEvent("first");
      expect(client.getSessionId()).toBe("sess-1");

      await expect(client.sendEvent("second")).rejects.toThrow(PermisoCustomHooksError);
      expect(client.getSessionId()).toBe("sess-1");
    });
  });

  describe("endSession", () => {
    it("sends stop event", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: () => Promise.resolve("{}"),
      });

      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      await client.endSession();

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.hook_event_name).toBe("stop");
      expect(body.hookEvent).toBe("stop");
    });
  });

  describe("getSessionId", () => {
    it("returns undefined before any successful response with sessionId", () => {
      const client = new PermisoCustomHooksClient({ baseUrl, apiKey });
      expect(client.getSessionId()).toBeUndefined();
    });
  });
});
