/**
 * Client API — base URL et fetch avec credentials (cookies).
 */

const API_BASE =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

type ApiError = { detail: string };

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    credentials: "include",
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const message =
      typeof (data as ApiError).detail === "string"
        ? (data as ApiError).detail
        : Array.isArray((data as { detail?: string[] }).detail)
          ? (data as { detail: string[] }).detail.join(", ")
          : "Erreur serveur";
    throw new Error(message);
  }

  return data as T;
}

export { API_BASE, request };
