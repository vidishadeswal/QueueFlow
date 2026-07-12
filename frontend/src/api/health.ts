import { apiClient } from "./client";

export interface HealthStatus {
  database: "up" | "down";
  redis: "up" | "down";
}

export async function fetchHealth(): Promise<HealthStatus> {
  const { data } = await apiClient.get<HealthStatus>("/health");
  return data;
}
