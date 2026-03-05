import { request, API_BASE } from "./client";

export type ScanItem = {
  id: string;
  status: string;
  created_at: string;
};

export type ScanDetail = {
  id: string;
  user_id: string;
  repository_url: string | null;
  upload_path: string | null;
  language: string | null;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type ScanCreatePayload = {
  repository_url?: string | null;
  upload_path?: string | null;
  language?: string | null;
};

export async function getMyScans(): Promise<ScanItem[]> {
  return request<ScanItem[]>("/api/scans/me");
}

export async function createScan(payload: ScanCreatePayload): Promise<ScanDetail> {
  return request<ScanDetail>("/api/scans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadScan(file: File): Promise<ScanDetail> {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${API_BASE}/api/scans/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Erreur lors du téléversement" }));
    throw new Error(error.detail || "Erreur lors du téléversement");
  }
  
  return response.json();
}

export async function getScan(scanId: string): Promise<ScanDetail> {
  return request<ScanDetail>(`/api/scans/${scanId}`);
}

export type ScanPreview = {
  scan_id: string;
  status: "ready" | "not_ready";
  message?: string;
  technologies: {
    python: boolean;
    javascript: boolean;
    typescript: boolean;
    php: boolean;
    java: boolean;
    go: boolean;
    ruby: boolean;
    rust: boolean;
    csharp: boolean;
  };
  tools: string[];
  files_by_type: {
    [key: string]: string[];
  };
  total_files: number;
  semgrep_configs: string[];
};

export async function getScanPreview(scanId: string): Promise<ScanPreview> {
  return request<ScanPreview>(`/api/scans/${scanId}/preview`);
}

export async function runScan(scanId: string): Promise<{ scan_id: string; status: string; message: string }> {
  return request<{ scan_id: string; status: string; message: string }>(`/api/scans/${scanId}/run`, {
    method: "POST",
  });
}

// Types pour la progression (simplifiés pour l'instant)
export type TaskProgress = {
  tool_name: string;
  display_name: string;
  status: string;
  progress: number;
  started_at: string | null;
  finished_at: string | null;
};

export type ScanProgress = {
  scan_id: string;
  scan_status: string;
  overall_progress: number;
  tasks: TaskProgress[];
};

export async function getScanProgress(scanId: string): Promise<ScanProgress> {
  // Pour l'instant, retourner une structure basique
  // TODO: Implémenter l'endpoint backend /api/scans/{scan_id}/progress
  const scan = await getScan(scanId);
  return {
    scan_id: scanId,
    scan_status: scan.status,
    overall_progress: scan.status === "completed" ? 100 : scan.status === "running" ? 50 : 0,
    tasks: [],
  };
}

// Types pour le score
export type ScanScore = {
  scan_id: string;
  score: number;
  grade: string;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  total_vulnerabilities: number;
};

// Types pour les résultats
export type VulnerabilityItem = {
  id: string;
  scan_id: string;
  title: string;
  description: string | null;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  severity: string;
  confidence: string | null;
  cve_id: string | null;
  cwe_id: string | null;
  owasp_category_id: string | null;
  owasp_category_name: string | null;
  status: string;
  created_at: string;
};

export type ScanResults = {
  scan_id: string;
  total: number;
  items: VulnerabilityItem[];
};

// Types pour OWASP
export type OwaspSummaryItem = {
  owasp_category_id: string;
  owasp_category_name: string;
  count: number;
};

export type ScanOwaspSummary = {
  scan_id: string;
  items: OwaspSummaryItem[];
};

export async function getScanScore(scanId: string): Promise<ScanScore> {
  return request<ScanScore>(`/api/scans/${scanId}/score`);
}

export async function getScanResults(scanId: string): Promise<ScanResults> {
  return request<ScanResults>(`/api/scans/${scanId}/results`);
}

export async function getScanOwaspSummary(scanId: string): Promise<ScanOwaspSummary> {
  return request<ScanOwaspSummary>(`/api/scans/${scanId}/owasp-summary`);
}

export type ScanFiles = {
  scan_id: string;
  total_files: number;
  files_by_tool: {
    [toolName: string]: {
      files: string[];
      count: number;
      status: string;
    };
  };
  all_files: string[];
};

export async function getScanFiles(scanId: string): Promise<ScanFiles> {
  return request<ScanFiles>(`/api/scans/${scanId}/files`);
}

export async function downloadScanReportPdf(scanId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/scans/${scanId}/report/pdf`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Erreur lors du téléchargement du rapport" }));
    throw new Error(error.detail || "Erreur lors du téléchargement du rapport");
  }

  // Créer un blob et télécharger le fichier
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `securescan_report_${scanId}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
