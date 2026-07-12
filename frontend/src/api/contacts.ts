import { apiClient } from "./client";

export interface Contact {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  created_at: string;
}

export interface ContactCreate {
  name: string;
  email: string;
  phone?: string;
}

export async function listContacts(): Promise<Contact[]> {
  const { data } = await apiClient.get<Contact[]>("/contacts");
  return data;
}

export async function createContact(payload: ContactCreate): Promise<Contact> {
  const { data } = await apiClient.post<Contact>("/contacts", payload);
  return data;
}

export async function deleteContact(id: string): Promise<void> {
  await apiClient.delete(`/contacts/${id}`);
}
