/**
 * Client API — base URL et fetch avec credentials (cookies).
 */

const API_BASE =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

type ApiError = { detail: string | string[] | unknown };

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
    let message = "Erreur serveur";
    
    // Extraire le message d'erreur de la réponse
    if (typeof (data as ApiError)?.detail === "string") {
      message = (data as ApiError).detail;
    } else if (Array.isArray((data as ApiError)?.detail)) {
      message = (data as { detail: string[] }).detail.join(", ");
    } else if (typeof data === "object" && data !== null && "message" in data) {
      message = (data as any).message;
    } else if (typeof data === "string") {
      message = data;
    }
    
    throw new Error(message);
  }

  return data as T;
}

export { API_BASE, request };
