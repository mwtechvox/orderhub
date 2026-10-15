import { afterEach, it, expect, vi } from "vitest";
import { api, post, resetAuth, setCompany } from "@/lib/api";
afterEach(() => {
  vi.unstubAllGlobals();
  resetAuth();
});
it("sends session cookies, CSRF and company header without local storage", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ csrfToken: "csrf" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ok: true })));
  vi.stubGlobal("fetch", fetch);
  setCompany("company-a");
  await post("/api/messages/send/", { text: "hi" });
  expect(fetch.mock.calls[1][1]).toMatchObject({
    credentials: "include",
    headers: { "X-CSRFToken": "csrf", "X-Company-ID": "company-a" },
  });
});
it("rejects provider URLs and shows safe backend errors", async () => {
  await expect(api("https://graph.facebook.com/me")).rejects.toThrow(
    "Invalid API path",
  );
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          code: "META_AUTH_ERROR",
          message: "Дахин холбоно уу.",
        }),
        { status: 502 },
      ),
    ),
  );
  await expect(api("/api/posts/")).rejects.toThrow("Дахин холбоно уу.");
});
