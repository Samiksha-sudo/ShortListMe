import { clearSession, loadSession, saveSession } from "./session";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, readonly kind: "network" | "http", readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

const NETWORK_MESSAGE = "ShortlistMe couldn't reach the server. Check your connection and try again.";

const isAuthPath = (path: string) => path.startsWith("/v1/auth/");

function withToken(init: RequestInit | undefined, token: string): RequestInit {
  return { ...init, headers: { ...(init?.headers as Record<string, string> | undefined), Authorization: `Bearer ${token}` } };
}

let refreshing: Promise<string | null> | null = null;

/** Trade the refresh token for a new access token; one request at a time, shared by concurrent callers. */
function refreshAccess(): Promise<string | null> {
  refreshing ??= (async () => {
    const session = loadSession();
    if (!session) return null;
    try {
      const res = await fetch(`${API_URL}/v1/auth/refresh`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: session.refresh_token }),
      });
      if (!res.ok) return null;
      const { access_token } = await res.json();
      saveSession({ ...session, access_token });
      return access_token as string;
    } catch {
      return null;
    }
  })().finally(() => { refreshing = null; });
  return refreshing;
}

/** fetch wrapper: adds the access token (refreshing it once on 401); network failures and non-2xx answers become ApiError. */
async function send(path: string, init: RequestInit | undefined, fallback: string): Promise<Response> {
  const attempt = (token: string | undefined) =>
    fetch(`${API_URL}${path}`, token ? withToken(init, token) : init);
  let res: Response;
  try {
    const authed = !isAuthPath(path);
    res = await attempt(authed ? loadSession()?.access_token : undefined);
    if (authed && res.status === 401) {
      const fresh = await refreshAccess();
      if (fresh) {
        res = await attempt(fresh);
      } else {
        // Session is gone for good: drop it and return to the login screen.
        clearSession();
        window.location.reload();
      }
    }
  } catch {
    throw new ApiError(NETWORK_MESSAGE, "network");
  }
  if (res.ok) return res;
  const body = await res.json().catch(() => null);
  const detail = body?.detail;
  // FastAPI validation errors arrive as a list; pydantic prefixes custom messages with "Value error, ".
  const message = Array.isArray(detail)
    ? detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, "")).join(" ")
    : typeof detail === "string" ? detail : undefined;
  throw new ApiError(message ?? `${fallback} (HTTP ${res.status})`, "http", res.status);
}

async function postJSON<T>(path: string, payload: unknown, fallback: string): Promise<T> {
  const res = await send(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }, fallback);
  return res.status === 204 ? (undefined as T) : res.json();
}

export async function getHealth(): Promise<{ status: string }> {
  const res = await send("/health", undefined, "Health check failed");
  return res.json();
}

/* ---------- auth ---------- */

export interface AuthResult {
  user: { id: string; email: string };
  access_token: string;
  refresh_token: string;
}

export const signup = (email: string, password: string) =>
  postJSON<AuthResult>("/v1/auth/signup", { email, password }, "Sign up failed");

export const login = (email: string, password: string) =>
  postJSON<AuthResult>("/v1/auth/login", { email, password }, "Log in failed");

export const forgotPassword = (email: string) =>
  postJSON<{ message: string }>("/v1/auth/forgot-password", { email }, "Could not send the reset link");

export const resetPassword = (token: string, password: string) =>
  postJSON<{ message: string }>("/v1/auth/reset-password", { token, password }, "Could not reset the password");

export const logout = (refreshToken: string) =>
  postJSON<void>("/v1/auth/logout", { refresh_token: refreshToken }, "Log out failed");

/* ---------- job descriptions ---------- */

export interface JobDescription {
  jd_id: string;
  text: string;
  text_hash: string;
  created_at: string;
}

export const saveJD = (text: string) =>
  postJSON<JobDescription>("/v1/jds", { text }, "Could not save the job description");

export async function getJD(jdId: string): Promise<JobDescription> {
  const res = await send(`/v1/jds/${jdId}`, undefined, "Could not load the job description");
  return res.json();
}

export type Seniority = "intern" | "junior" | "mid" | "senior" | "lead" | "principal" | "unspecified";

export interface JobAnalysis {
  jd_id: string;
  cached: boolean;
  role_title: string;
  seniority: Seniority;
  required_skills: string[];
  nice_to_haves: string[];
  responsibilities: string[];
  ats_keywords: string[];
}

export const analyseJD = (jdId: string) =>
  postJSON<JobAnalysis>(`/v1/jds/${jdId}/analysis`, {}, "Could not analyse the job description");

/* ---------- CVs ---------- */

export interface UploadedCV {
  cv_id: string;
  filename: string;
  size: number;
  blocks: number;
  editable: number;
}

export type BlockType =
  | "name" | "contact" | "headline" | "heading" | "summary"
  | "role_title" | "bullet" | "skill_line" | "other";

export interface Block {
  id: string;
  type: BlockType;
  section: string;
  text: string;
  editable: boolean;
  parent_id: string | null;
}

export interface ParsedCV {
  cv_id: string;
  filename: string;
  sections: string[];
  blocks: Block[];
  facts: { numbers: string[]; entities: string[]; skills: string[]; headline_seniority: string[] };
}

export async function getCV(cvId: string): Promise<ParsedCV> {
  const res = await send(`/v1/cvs/${cvId}`, undefined, "Could not load your CV");
  return res.json();
}

export async function uploadCV(file: File): Promise<UploadedCV> {
  const form = new FormData();
  form.append("file", file);
  const res = await send("/v1/cvs", { method: "POST", body: form }, "Upload failed");
  return res.json();
}

/* ---------- match and tailoring ---------- */

export type MatchStatus = "covered" | "weak" | "gap";

export interface MatchItem {
  requirement: string;
  kind: "must" | "nice";
  status: MatchStatus;
  evidence: string | null;
}

export interface MatchResult {
  score: number;
  covered: number;
  weak: number;
  gaps: number;
  items: MatchItem[];
}

export const createMatch = (cvId: string, jdId: string) =>
  postJSON<MatchResult & { cv_id: string; jd_id: string }>(
    "/v1/matches", { cv_id: cvId, jd_id: jdId }, "Could not match your CV to the job");

export interface ProposedEdit {
  block_id: string;
  new_text: string;
  rationale: string;
  added_keywords: string[];
}

export interface DroppedEdit {
  block_id: string;
  reason: string;
}

export interface TailoringJob {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  step: string;
  steps: string[];
  error: string | null;
  result: { match: MatchResult; edits: ProposedEdit[]; dropped: DroppedEdit[] } | null;
}

export const startTailoring = (cvId: string, jdId: string) =>
  postJSON<TailoringJob>("/v1/tailoring", { cv_id: cvId, jd_id: jdId }, "Could not start tailoring");

export async function getTailoring(jobId: string): Promise<TailoringJob> {
  const res = await send(`/v1/tailoring/${jobId}`, undefined, "Could not check progress");
  return res.json();
}

/** Apply the accepted changes to the original CV and return the finished file with a filename. */
export async function exportCV(cvId: string, format: "docx" | "pdf", edits: Record<string, string>): Promise<{ blob: Blob; filename: string }> {
  const res = await send(`/v1/cvs/${cvId}/export.${format}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ edits }),
  }, `Could not create your ${format.toUpperCase()}`);
  const m = /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "");
  return { blob: await res.blob(), filename: m?.[1] ?? `tailored-cv.${format}` };
}

/* ---------- billing ---------- */

export interface Usage {
  plan: "free" | "pro" | "admin";
  used: number;
  limit: number;
  remaining: number;
}

export async function getUsage(): Promise<Usage> {
  const res = await send("/v1/billing", undefined, "Could not load your plan");
  return res.json();
}

export const startCheckout = () =>
  postJSON<{ url: string }>("/v1/billing/checkout", {}, "Could not start checkout");

export const openPortal = () =>
  postJSON<{ url: string }>("/v1/billing/portal", {}, "Could not open subscription settings");
