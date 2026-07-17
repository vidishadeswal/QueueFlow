import { apiClient } from "./client";
import type { Page } from "./pagination";

export interface Appointment {
  id: string;
  contact_id: string;
  title: string;
  scheduled_at: string;
  notes: string | null;
  created_at: string;
}

export interface AppointmentCreate {
  contact_id: string;
  title: string;
  scheduled_at: string;
  notes?: string;
}

// Requests the max page size the API allows; this dashboard doesn't yet have
// a pager UI, so this is "show everything up to the safety cap" for now.
export async function listAppointments(): Promise<Appointment[]> {
  const { data } = await apiClient.get<Page<Appointment>>("/appointments", { params: { limit: 200 } });
  return data.items;
}

export async function createAppointment(payload: AppointmentCreate): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>("/appointments", payload);
  return data;
}

export async function deleteAppointment(id: string): Promise<void> {
  await apiClient.delete(`/appointments/${id}`);
}
