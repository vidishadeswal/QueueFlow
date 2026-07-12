import { apiClient } from "./client";

export interface Business {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface SignupPayload {
  name: string;
  email: string;
  password: string;
}

export async function signup(payload: SignupPayload): Promise<Business> {
  const { data } = await apiClient.post<Business>("/auth/signup", payload);
  return data;
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  const { data } = await apiClient.post<{ access_token: string }>("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data.access_token;
}

export async function fetchMe(): Promise<Business> {
  const { data } = await apiClient.get<Business>("/auth/me");
  return data;
}
