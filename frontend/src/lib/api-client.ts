let csrfToken: string | null = null;
let companyId: string | null = null;

export function setActiveCompany(id: string | null) {
  companyId = id;
}

export function resetApiSession() {
  csrfToken = null;
  companyId = null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public data: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorMessage(payload: unknown): { code: string; message: string } {
  if (!payload || typeof payload !== "object") {
    return { code: "REQUEST_FAILED", message: "Хүсэлт амжилтгүй боллоо." };
  }
  const data = payload as Record<string, unknown>;
  if (typeof data.message === "string") {
    return {
      code: String(data.code ?? "REQUEST_FAILED"),
      message: data.message,
    };
  }
  if (typeof data.detail === "string") {
    return { code: String(data.code ?? "REQUEST_FAILED"), message: data.detail };
  }
  const first = Object.values(data)[0];
  if (Array.isArray(first) && typeof first[0] === "string") {
    return { code: "VALIDATION_ERROR", message: first[0] };
  }
  if (typeof first === "string") {
    return { code: "VALIDATION_ERROR", message: first };
  }
  return { code: "REQUEST_FAILED", message: "Хүсэлт амжилтгүй боллоо." };
}

async function getCsrfToken() {
  const response = await fetch("/api/auth/csrf/", { credentials: "include" });
  const payload = (await response.json().catch(() => null)) as {
    csrfToken?: string;
  } | null;
  if (!response.ok || !payload?.csrfToken) {
    throw new ApiError(response.status, "CSRF", "Сервертэй холбогдох боломжгүй.", payload);
  }
  csrfToken = payload.csrfToken;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!path.startsWith("/api/")) throw new Error("Invalid API path");
  const method = (init.method ?? "GET").toUpperCase();
  const mutating = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (mutating && !csrfToken) await getCsrfToken();

  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(companyId ? { "X-Company-ID": companyId } : {}),
      ...(mutating && csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...init.headers,
    },
  });
  const payload: unknown = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const error = errorMessage(payload);
    throw new ApiError(response.status, error.code, error.message, payload);
  }
  if (payload && typeof payload === "object" && "csrfToken" in payload) {
    csrfToken = String((payload as { csrfToken: string }).csrfToken);
  }
  return payload as T;
}

export function post<T>(path: string, body: unknown = {}) {
  return api<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export function put<T>(path: string, body: unknown) {
  return api<T>(path, { method: "PUT", body: JSON.stringify(body) });
}

export function patch<T>(path: string, body: unknown) {
  return api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}
