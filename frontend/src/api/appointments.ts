import { apiClient } from "./client";

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

export async function listAppointments(): Promise<Appointment[]> {
  const { data } = await apiClient.get<Appointment[]>("/appointments");
  return data;
}

export async function createAppointment(payload: AppointmentCreate): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>("/appointments", payload);
  return data;
}

export async function deleteAppointment(id: string): Promise<void> {
  await apiClient.delete(`/appointments/${id}`);
}
