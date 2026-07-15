import { env } from "./env";
import type { PingLatest } from "@/types/ping";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${env.apiBaseUrl}${path}`);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getLatestPingResults: () => request<PingLatest[]>("/api/v1/ping/latest"),
};
