import { apiClient } from "./client";

export interface AnalyticsSummary {
  today_reminders: number;
  failed_reminders: number;
  dead_letter_reminders: number;
  upcoming_reminders: number;
  delivery_rate: number | null;
  avg_retry_count: number;
  queue_size: number;
  worker_healthy: boolean;
}

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const { data } = await apiClient.get<AnalyticsSummary>("/analytics/summary");
  return data;
}
