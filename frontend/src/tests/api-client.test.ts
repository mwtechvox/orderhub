import { afterEach, describe, expect, it, vi } from "vitest";
import { api, post, resetApiSession, setActiveCompany } from "@/lib/api-client";

afterEach(() => {
  vi.unstubAllGlobals();
  resetApiSession();
});

describe("api client", () => {
  it("sends the active company on reads", async () => {
    setActiveCompany("company-1");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await api("/api/example/");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/example/",
      expect.objectContaining({
        credentials: "include",
        headers: expect.objectContaining({ "X-Company-ID": "company-1" }),
      }),
    );
  });

  it("fetches CSRF before a mutation and preserves tenant context", async () => {
    setActiveCompany("company-2");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrfToken: "csrf-value" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    await post("/api/example/", { value: 1 });
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/auth/csrf/", {
      credentials: "include",
    });
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/example/",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        headers: expect.objectContaining({
          "X-CSRFToken": "csrf-value",
          "X-Company-ID": "company-2",
        }),
      }),
    );
  });
});
