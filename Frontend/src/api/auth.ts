import type { User } from "../types";
import { request } from "./client";

export type { User };

export async function register(data: {
  email: string;
  password: string;
  full_name?: string | null;
}): Promise<User> {
  return request<User>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function login(data: {
  email: string;
  password: string;
}): Promise<User> {
  return request<User>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function logout(): Promise<{ message: string }> {
  return request("/api/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<User> {
  return request<User>("/api/auth/me");
}
