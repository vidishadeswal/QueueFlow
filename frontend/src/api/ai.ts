import { apiClient } from "./client";

export type ReminderTone = "friendly" | "formal" | "promotional";

export interface DraftReminderRequest {
  appointment_id: string;
  tone?: ReminderTone;
  custom_prompt?: string;
}

export async function draftReminderMessage(payload: DraftReminderRequest): Promise<string> {
  const { data } = await apiClient.post<{ message: string }>("/ai/draft-reminder", payload);
  return data.message;
}
