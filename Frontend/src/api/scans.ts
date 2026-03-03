import { request } from "./client";

export type ScanItem = {
  id: string;
  status: string;
  created_at: string;
};

export async function getMyScans(): Promise<ScanItem[]> {
  return request<ScanItem[]>("/api/scans/me");
}
