import { apiClient } from "./client";
import type { Page } from "./pagination";

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

// Requests the max page size the API allows; this dashboard doesn't yet have
// a pager UI, so this is "show everything up to the safety cap" for now.
export async function listReminders(): Promise<Reminder[]> {
  const { data } = await apiClient.get<Page<Reminder>>("/reminders", { params: { limit: 200 } });
  return data.items;
}

// idempotencyKey, when passed, lets a retried submission (e.g. after a dropped
// connection) safely resolve to the same reminder instead of creating a duplicate.
export async function createReminder(payload: ReminderCreate, idempotencyKey?: string): Promise<Reminder> {
  const { data } = await apiClient.post<Reminder>("/reminders", payload, {
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
  });
  return data;
}

export async function retryReminder(id: string): Promise<Reminder> {
  const { data } = await apiClient.post<Reminder>(`/reminders/${id}/retry`);
  return data;
}

export async function deleteReminder(id: string): Promise<void> {
  await apiClient.delete(`/reminders/${id}`);
}
