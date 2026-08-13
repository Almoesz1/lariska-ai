const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Backend belum dapat dihubungi. Pastikan FastAPI berjalan di port 8000.", 0);
  }

  if (response.ok) return response.json() as Promise<T>;

  const payload = await response.json().catch(() => null);
  const detail = typeof payload?.detail === "string" ? payload.detail : "Permintaan ke backend gagal.";
  throw new ApiError(detail, response.status);
}

export { API_BASE_URL };
