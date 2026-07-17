import { apiClient } from "./client";

export type ReminderStatus = "pending" | "queued" | "sent" | "dead_letter";

export interface Reminder {
  id: string;
  appointment_id: string;
  contact_id: string;
  message: string;
  send_at: string;
  status: ReminderStatus;
  retry_count: number;
  last_error: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface ReminderCreate {
  appointment_id: string;
  message: string;
  send_at: string;
}

export async function listReminders(): Promise<Reminder[]> {
  const { data } = await apiClient.get<Reminder[]>("/reminders");
  return data;
}

export async function createReminder(payload: ReminderCreate): Promise<Reminder> {
  const { data } = await apiClient.post<Reminder>("/reminders", payload);
  return data;
}

export async function retryReminder(id: string): Promise<Reminder> {
  const { data } = await apiClient.post<Reminder>(`/reminders/${id}/retry`);
  return data;
}

export async function deleteReminder(id: string): Promise<void> {
  await apiClient.delete(`/reminders/${id}`);
}
