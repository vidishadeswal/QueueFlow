import { apiClient } from "./client";
import type { Page } from "./pagination";

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

// Requests the max page size the API allows; this dashboard doesn't yet have
// a pager UI, so this is "show everything up to the safety cap" for now.
export async function listContacts(): Promise<Contact[]> {
  const { data } = await apiClient.get<Page<Contact>>("/contacts", { params: { limit: 200 } });
  return data.items;
}

export async function createContact(payload: ContactCreate): Promise<Contact> {
  const { data } = await apiClient.post<Contact>("/contacts", payload);
  return data;
}

export async function deleteContact(id: string): Promise<void> {
  await apiClient.delete(`/contacts/${id}`);
}
