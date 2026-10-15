export const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
let csrfToken: string | null = null;
let companyId: string | null = null;
export function setCompany(id: string | null) {
  companyId = id;
}
export function resetAuth() {
  csrfToken = null;
  companyId = null;
}
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!path.startsWith("/api/")) throw new Error("Invalid API path");
  const mutating = !["GET", "HEAD", "OPTIONS"].includes(init.method ?? "GET");
  if (mutating && !csrfToken) {
    const response = await fetch(`${API_URL}/api/auth/csrf/`, {
      credentials: "include",
    });
    if (!response.ok)
      throw new ApiError(
        response.status,
        "CSRF",
        "Сервертэй холбогдох боломжгүй.",
      );
    csrfToken = (await response.json()).csrfToken;
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(companyId ? { "X-Company-ID": companyId } : {}),
      ...(mutating && csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...init.headers,
    },
  });
  const payload =
    response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      response.status,
      payload?.code ?? "REQUEST_FAILED",
      payload?.message ?? "Хүсэлт амжилтгүй. Дахин оролдоно уу.",
    );
  if (payload?.csrfToken) csrfToken = payload.csrfToken;
  return payload as T;
}
export const post = <T>(path: string, body: unknown = {}) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
