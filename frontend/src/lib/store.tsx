import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

/*
 * Device-local workspace. The backend has no endpoints to list a user's CVs, jobs or applications,
 * so what the user has done in this browser is remembered here (localStorage, per account).
 * It is a convenience record, not account history: another device or browser will not see it.
 */

export type AppStage = "draft" | "analysed" | "tailored";
export type AppStatus = "Draft" | "Analysed" | "Tailored" | "Needs review" | "Ready";

export interface CVRecord { id: string; filename: string; size: number; at: number }

export interface AppRecord {
  id: string; // `${cvId}:${jdId}`
  cvId: string;
  jdId: string;
  cvName: string;
  company: string;
  role: string | null;
  seniority: string | null;
  jdPreview: string;
  stage: AppStage;
  jobId: string | null;
  score: number | null;
  suggested: number;
  removed: number;
  gaps: number;
  accepted: number;
  rejected: number;
  at: number;
}

export interface Decision { status: "accepted" | "rejected"; text?: string }

export interface Current { cvId: string | null; jdId: string | null; jobId: string | null; step: number }

interface Workspace {
  cvs: CVRecord[];
  apps: AppRecord[];
  current: Current;
  decisions: Record<string, Record<string, Decision>>; // jobId -> blockId -> decision
}

const EMPTY: Workspace = { cvs: [], apps: [], current: { cvId: null, jdId: null, jobId: null, step: 0 }, decisions: {} };

export const appId = (cvId: string, jdId: string) => `${cvId}:${jdId}`;

export function appStatus(a: AppRecord): AppStatus {
  if (a.stage === "draft") return "Draft";
  if (a.stage === "analysed") return "Analysed";
  const decided = a.accepted + a.rejected;
  if (a.suggested === 0 || decided === 0) return "Tailored";
  return decided >= a.suggested ? "Ready" : "Needs review";
}

const blankApp = (cvId: string, jdId: string): AppRecord => ({
  id: appId(cvId, jdId), cvId, jdId, cvName: "", company: "", role: null, seniority: null, jdPreview: "",
  stage: "draft", jobId: null, score: null, suggested: 0, removed: 0, gaps: 0, accepted: 0, rejected: 0, at: Date.now(),
});

function load(key: string): Workspace {
  try {
    const raw = JSON.parse(localStorage.getItem(key) ?? "null") as Partial<Workspace> | null;
    return raw ? { ...EMPTY, ...raw, current: { ...EMPTY.current, ...raw.current } } : EMPTY;
  } catch {
    return EMPTY;
  }
}

function recount(apps: AppRecord[], jobId: string, decisions: Record<string, Decision>): AppRecord[] {
  const values = Object.values(decisions);
  return apps.map((a) => a.jobId === jobId
    ? { ...a, accepted: values.filter((d) => d.status === "accepted").length,
        rejected: values.filter((d) => d.status === "rejected").length, at: Date.now() }
    : a);
}

interface Actions {
  setCurrent: (patch: Partial<Current>) => void;
  addCV: (cv: CVRecord) => void;
  upsertApp: (patch: Partial<AppRecord> & { cvId: string; jdId: string }) => void;
  decide: (jobId: string, blockId: string, decision: Decision | null) => void;
  decideMany: (jobId: string, entries: Record<string, Decision>) => void;
  resetCurrent: () => void;
  clearAll: () => void;
}

type Api = Actions & { state: Workspace };
const Ctx = createContext<Api | null>(null);

export function WorkspaceProvider({ userId, children }: { userId: string; children: ReactNode }) {
  const key = `shortlistme.workspace.${userId}`;
  const [state, setState] = useState<Workspace>(() => load(key));

  useEffect(() => { localStorage.setItem(key, JSON.stringify(state)); }, [key, state]);

  const actions = useMemo<Actions>(() => ({
    setCurrent: (patch) => setState((s) => ({ ...s, current: { ...s.current, ...patch } })),
    addCV: (cv) => setState((s) => ({ ...s, cvs: [cv, ...s.cvs.filter((c) => c.id !== cv.id)] })),
    upsertApp: ({ cvId, jdId, ...patch }) => setState((s) => {
      const id = appId(cvId, jdId);
      const existing = s.apps.find((a) => a.id === id) ?? blankApp(cvId, jdId);
      const next = { ...existing, ...patch, at: Date.now() };
      return { ...s, apps: [next, ...s.apps.filter((a) => a.id !== id)] };
    }),
    decide: (jobId, blockId, decision) => setState((s) => {
      const map = { ...(s.decisions[jobId] ?? {}) };
      if (decision) map[blockId] = decision;
      else delete map[blockId];
      return { ...s, decisions: { ...s.decisions, [jobId]: map }, apps: recount(s.apps, jobId, map) };
    }),
    decideMany: (jobId, entries) => setState((s) => {
      const map = { ...(s.decisions[jobId] ?? {}), ...entries };
      return { ...s, decisions: { ...s.decisions, [jobId]: map }, apps: recount(s.apps, jobId, map) };
    }),
    resetCurrent: () => setState((s) => ({ ...s, current: { ...EMPTY.current } })),
    clearAll: () => setState(EMPTY),
  }), []);

  const value = useMemo<Api>(() => ({ ...actions, state }), [actions, state]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWorkspace(): Api {
  const api = useContext(Ctx);
  if (!api) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return api;
}
