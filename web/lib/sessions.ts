// Typed client for the session REST API; types are generated from openapi.json (SPECS S3.7).
import type { components } from "./api-schema";

export type SessionSummary = components["schemas"]["SessionSummary"];
export type SessionPage = components["schemas"]["SessionPage"];
export type SessionDetail = components["schemas"]["SessionDetail"];
export type DownloadItem = components["schemas"]["DownloadItem"];
type ErrorBody = components["schemas"]["ErrorBody"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/sessions${path}`, {
    ...init,
    headers: { "content-type": "application/json" },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorBody | null;
    throw new ApiError(
      response.status,
      body?.error.code ?? "http_error",
      body?.error.message ?? `Request failed with status ${response.status}`,
    );
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const sessionsApi = {
  list(limit = 20, cursor?: string | null): Promise<SessionPage> {
    const query = new URLSearchParams({ limit: String(limit) });
    if (cursor) query.set("cursor", cursor);
    return call(`?${query}`);
  },
  create(name: string): Promise<SessionSummary> {
    return call("", { method: "POST", body: JSON.stringify({ name }) });
  },
  get(id: string): Promise<SessionDetail> {
    return call(`/${encodeURIComponent(id)}`);
  },
  rename(id: string, name: string): Promise<SessionSummary> {
    return call(`/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ name }) });
  },
  downloads(id: string): Promise<DownloadItem[]> {
    return call(`/${encodeURIComponent(id)}/downloads`);
  },
  remove(id: string): Promise<void> {
    return call(`/${encodeURIComponent(id)}`, { method: "DELETE" });
  },
};

const STAGE_LABELS: Record<string, string> = {
  interview: "Interview",
  design_review: "Design review",
  gap_resolution: "Gap resolution",
  prd_draft: "PRD draft",
  prd_signoff: "PRD sign-off",
  spec_synthesis: "Spec synthesis",
  seam_gate: "Seam approval",
  change_review: "Change review",
  ticket_breakdown: "Ticket breakdown",
  ticket_gate: "Ticket review",
  complete: "Complete",
};

export function stageLabel(stage: string, step?: number): string {
  const label = STAGE_LABELS[stage] ?? stage;
  return stage === "interview" && step ? `${label} · step ${step} of 5` : label;
}

/** SPECS S10.2: the file name each download kind is saved under. */
export function downloadFileName(kind: string, sessionName: string): string {
  const names: Record<string, string> = {
    "prd-v1.0.docx": "PRD v1.0.docx",
    "prd-v1.1.docx": "PRD v1.1.docx",
    "prd-v1.2.docx": "PRD v1.2.docx",
    "requirements.docx": "Requirements.docx",
    "user-stories.docx": "UserStories.docx",
    "context.md": "context.md",
    "bundle.zip": `${sessionName} - Blueprint.zip`,
  };
  return names[kind] ?? kind;
}

export function downloadUrl(sessionId: string, kind: string): string {
  return `/api/sessions/${encodeURIComponent(sessionId)}/downloads/${encodeURIComponent(kind)}`;
}
