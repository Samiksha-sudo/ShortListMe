import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, analyseJD, createMatch, exportCV, getCV, getJD, getTailoring, saveJD, startTailoring } from "../api";
import { plural } from "../lib/format";
import { appId, useWorkspace } from "../lib/store";
import { PageHeader } from "../ui/AppShell";
import { QuotaReached, useUsage, usageLine } from "../ui/Billing";
import { CVReady, UploadDropzone } from "../ui/CV";
import Icon from "../ui/Icon";
import { AnalysisPanel, GapCoaching, MatchCard, RequirementMatrix } from "../ui/Match";
import ProgressStepper from "../ui/ProgressStepper";
import { Alert, Button, Card, CardHead, EmptyState, ErrorState, Modal, SkeletonRows } from "../ui/primitives";
import { EditCard, RemovedList, TruthCheck } from "../ui/Review";

const MIN_JD = 100;
const MAX_JD = 20000;

/* ---------- step 0: CV ---------- */
function StepCV({ onNext }: { onNext: () => void }) {
  const { state, setCurrent, addCV } = useWorkspace();
  const { cvId } = state.current;
  const cv = useQuery({ queryKey: ["cv", cvId], queryFn: () => getCV(cvId!), enabled: !!cvId, staleTime: Infinity });
  const change = () => setCurrent({ cvId: null, jdId: null, jobId: null, step: 0 });

  if (!cvId) {
    return (
      <div style={{ display: "grid", gap: 20 }}>
        <UploadDropzone onUploaded={(u) => {
          addCV({ id: u.cv_id, filename: u.filename, size: u.size, at: Date.now() });
          setCurrent({ cvId: u.cv_id, jdId: null, jobId: null, step: 0 });
        }} />
        {state.cvs.length > 0 && (
          <Card>
            <CardHead title="Or use a CV you uploaded on this device" />
            <div style={{ display: "grid", gap: 8 }}>
              {state.cvs.slice(0, 4).map((c) => (
                <div key={c.id} className="settings-row">
                  <span className="cv-row"><span className="file-ico"><Icon name="file" /></span>{c.filename}</span>
                  <Button size="sm" onClick={() => setCurrent({ cvId: c.id, jdId: null, jobId: null })}>Use this CV</Button>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    );
  }
  if (cv.isPending) return <Card><SkeletonRows rows={5} /></Card>;
  if (cv.isError) {
    return (
      <div style={{ display: "grid", gap: 16 }}>
        <ErrorState title="Couldn't open your CV" message={cv.error.message} onRetry={() => void cv.refetch()} />
        <div><Button onClick={change}>Upload a different CV</Button></div>
      </div>
    );
  }
  return (
    <CVReady cv={cv.data} actions={
      <span style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Button variant="ghost" onClick={change}>Use a different CV</Button>
        <Button variant="primary" iconRight="arrowRight" onClick={onNext}>Add a job</Button>
      </span>
    } />
  );
}

/* ---------- step 1: job description + analysis ---------- */
function StepJD({ onNext }: { onNext: () => void }) {
  const { state, setCurrent, upsertApp } = useWorkspace();
  const { cvId, jdId } = state.current;
  const existing = state.apps.find((a) => a.id === (cvId && jdId ? appId(cvId, jdId) : ""));
  const [text, setText] = useState("");
  const [company, setCompany] = useState(existing?.company ?? "");
  const [touched, setTouched] = useState(false);

  const saved = useQuery({ queryKey: ["jd", jdId], queryFn: () => getJD(jdId!), enabled: !!jdId, staleTime: Infinity });
  const savedText = saved.data?.text;
  useEffect(() => { if (savedText !== undefined) setText((t) => t || savedText); }, [savedText]);

  const analysis = useQuery({ queryKey: ["analysis", jdId], queryFn: () => analyseJD(jdId!), enabled: !!jdId, staleTime: Infinity, retry: false });
  const save = useMutation({ mutationFn: () => saveJD(text), onSuccess: (jd) => setCurrent({ jdId: jd.jd_id, jobId: null }) });

  const record = (stage: "analysed") => {
    if (!cvId || !jdId || !analysis.data) return;
    upsertApp({
      cvId, jdId, company: company.trim(), role: analysis.data.role_title || null,
      seniority: analysis.data.seniority === "unspecified" ? null : analysis.data.seniority,
      jdPreview: text.trim().slice(0, 160), cvName: state.cvs.find((c) => c.id === cvId)?.filename ?? "",
      ...(existing && existing.stage !== "draft" ? {} : { stage }),
    });
  };
  const analysedId = analysis.data?.jd_id;
  useEffect(() => { if (analysedId) record("analysed"); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [analysedId]);

  const length = text.trim().length;
  const tooShort = length < MIN_JD;
  const tooLong = length > MAX_JD;
  const unchanged = !!savedText && text.trim() === savedText.trim();
  const analyse = () => {
    setTouched(true);
    if (tooShort || tooLong) return;
    if (!unchanged) save.mutate();
    else void analysis.refetch();
  };
  const busy = save.isPending || (!!jdId && analysis.isFetching && !analysis.data);

  return (
    <div className="split">
      <Card>
        <CardHead title="The role" subtitle="Paste the full job description. The more complete it is, the better the match." />
        <div className="field">
          <label htmlFor="company">Company <span className="muted" style={{ fontWeight: 400 }}>(optional, for your own records)</span></label>
          <input id="company" className="input" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Acme Ltd" autoComplete="organization" />
        </div>
        <div className="field" style={{ marginBottom: 8 }}>
          <label htmlFor="jd">Job description</label>
          <textarea id="jd" className="textarea" style={{ minHeight: 320 }} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Paste the job description here…" aria-describedby="jd-count" aria-invalid={touched && (tooShort || tooLong) ? true : undefined} />
        </div>
        <div id="jd-count" className={`counter${touched && (tooShort || tooLong) ? " bad" : ""}`}>
          <span>{tooLong ? `Too long — keep it under ${MAX_JD.toLocaleString()} characters.` : tooShort ? `Add at least ${MIN_JD} characters so there's enough to analyse.` : "Looks good."}</span>
          <span>{length.toLocaleString()} / {MAX_JD.toLocaleString()}</span>
        </div>
        <div className={`counter-bar${tooLong ? " bad" : ""}`}><i style={{ width: `${Math.min(100, (length / MAX_JD) * 100)}%` }} /></div>
        {save.isError && <ErrorState title="Couldn't save the job description" message={save.error.message} />}
        <div className="flow-nav" style={{ marginTop: 16 }}>
          <span />
          <Button variant="primary" size="lg" icon="target" loading={busy} onClick={analyse}>{busy ? "Analysing…" : "Analyse this role"}</Button>
        </div>
      </Card>

      <div style={{ display: "grid", gap: 16 }}>
        {!jdId && !save.isPending && (
          <Card><EmptyState icon="target" title="Your analysis will appear here" compact>
            ShortlistMe will pull out the skills, responsibilities and keywords this role cares about.
          </EmptyState></Card>
        )}
        {jdId && analysis.isPending && <Card><h2 style={{ marginBottom: 16 }}>Reading the job description…</h2><SkeletonRows rows={6} /></Card>}
        {jdId && analysis.isError && <ErrorState title="Couldn't analyse this role" message={analysis.error.message} onRetry={() => void analysis.refetch()} />}
        {analysis.data && jdId && (
          <>
            <AnalysisPanel analysis={analysis.data} />
            <Button variant="primary" size="lg" iconRight="arrowRight" onClick={() => { record("analysed"); onNext(); }}>See how your CV matches</Button>
          </>
        )}
      </div>
    </div>
  );
}

/* ---------- step 2: match intelligence ---------- */
function StepMatch({ onNext }: { onNext: () => void }) {
  const { state, upsertApp } = useWorkspace();
  const { cvId, jdId } = state.current;
  const match = useQuery({ queryKey: ["match", cvId, jdId], queryFn: () => createMatch(cvId!, jdId!), enabled: !!cvId && !!jdId, staleTime: Infinity, retry: false });
  const analysis = useQuery({ queryKey: ["analysis", jdId], queryFn: () => analyseJD(jdId!), enabled: !!jdId, staleTime: Infinity, retry: false });

  const score = match.data?.score;
  useEffect(() => {
    if (cvId && jdId && match.data) upsertApp({ cvId, jdId, score: match.data.score, gaps: match.data.gaps });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [score]);

  if (match.isPending) {
    return (
      <Card><h2 style={{ marginBottom: 6 }}>Comparing requirements with your CV…</h2>
        <p className="muted" style={{ marginBottom: 16 }}>This usually takes a few seconds.</p><SkeletonRows rows={6} /></Card>
    );
  }
  if (match.isError) return <ErrorState title="Couldn't compare your CV with this role" message={match.error.message} onRetry={() => void match.refetch()} />;

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <MatchCard match={match.data} />
      <RequirementMatrix match={match.data} />
      <GapCoaching match={match.data} />
      {analysis.data && <details className="details"><summary>What the role asks for</summary><AnalysisPanel analysis={analysis.data} /></details>}
      <div className="flow-nav">
        <span />
        <Button variant="primary" size="lg" icon="wand" onClick={onNext}>Tailor my CV</Button>
      </div>
    </div>
  );
}

/* ---------- step 3: tailoring progress ---------- */
const RUN_STEPS: { key: string; title: string; note: string }[] = [
  { key: "analysing", title: "Reading job requirements", note: "Working out what the role really asks for." },
  { key: "matching", title: "Comparing requirements with your CV", note: "Looking for real evidence in your experience." },
  { key: "rewriting", title: "Improving relevant experience", note: "Every proposed change is validated against your CV before you see it." },
  { key: "done", title: "Preparing review", note: "Getting your suggestions ready." },
];

function StepRun({ onDone }: { onDone: () => void }) {
  const { state, setCurrent, upsertApp } = useWorkspace();
  const { cvId, jdId, jobId } = state.current;
  const startedHere = useRef(false);
  const qc = useQueryClient();
  const start = useMutation({
    mutationFn: () => startTailoring(cvId!, jdId!),
    onSuccess: (j) => { setCurrent({ jobId: j.job_id }); void qc.invalidateQueries({ queryKey: ["billing"] }); },
  });

  useEffect(() => {
    if (!jobId && !startedHere.current) { startedHere.current = true; start.mutate(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const job = useQuery({
    queryKey: ["job", jobId], queryFn: () => getTailoring(jobId!), enabled: !!jobId,
    refetchInterval: (q) => (q.state.data?.status === "done" || q.state.data?.status === "failed" ? false : 1500),
  });

  const status = job.data?.status;
  const result = job.data?.result;
  useEffect(() => {
    if (status !== "done" || !result || !cvId || !jdId || !jobId) return;
    upsertApp({ cvId, jdId, stage: "tailored", jobId, score: result.match.score, gaps: result.match.gaps, suggested: result.edits.length, removed: result.dropped.length });
    if (startedHere.current) onDone();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const retry = () => { startedHere.current = false; start.reset(); setCurrent({ jobId: null }); };

  if (start.error instanceof ApiError && start.error.status === 402) return <QuotaReached message={start.error.message} />;
  if (start.isError) return <ErrorState title="Couldn't start tailoring" message={start.error.message} onRetry={retry} />;
  if (status === "failed") return <ErrorState title="Tailoring didn't finish" message={job.data?.error ?? "Something went wrong while tailoring your CV."} onRetry={retry} />;
  if (job.isError) return <ErrorState title="Couldn't check progress" message={job.error.message} onRetry={() => void job.refetch()} />;

  if (status === "done") {
    return (
      <Card className="run"><EmptyState icon="check" title="Tailoring complete">
        {plural(result?.edits.length ?? 0, "suggestion")} ready for your review.
      </EmptyState><div style={{ textAlign: "center" }}><Button variant="primary" onClick={onDone}>Review changes</Button></div></Card>
    );
  }

  const current = Math.max(0, RUN_STEPS.findIndex((s) => s.key === job.data?.step));
  return (
    <Card className="run">
      <div><h2>Tailoring your CV</h2><p className="muted">This takes a minute or so. You can stay on this page.</p></div>
      <ol className="run-steps" aria-live="polite">
        {RUN_STEPS.map((s, i) => {
          const cls = i < current ? "done" : i === current ? "active" : "todo";
          return (
            <li key={s.key} className={`run-step ${cls}`}>
              <span className="run-dot">{i < current ? <Icon name="check" /> : i + 1}</span>
              <div><h3>{s.title}{cls === "active" && <span className="sr-only"> (in progress)</span>}</h3>{cls !== "todo" && <p>{s.note}</p>}</div>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

/* ---------- step 4: review ---------- */
function StepReview({ onNext }: { onNext: () => void }) {
  const { state, decide, decideMany } = useWorkspace();
  const { cvId, jobId } = state.current;
  const [confirm, setConfirm] = useState(false);
  const job = useQuery({ queryKey: ["job", jobId], queryFn: () => getTailoring(jobId!), enabled: !!jobId, staleTime: Infinity });
  const cv = useQuery({ queryKey: ["cv", cvId], queryFn: () => getCV(cvId!), enabled: !!cvId, staleTime: Infinity });
  const decisions = (jobId && state.decisions[jobId]) || {};
  const blocks = useMemo(() => new Map((cv.data?.blocks ?? []).map((b) => [b.id, b])), [cv.data]);

  if (job.isPending || cv.isPending) return <Card><SkeletonRows rows={6} /></Card>;
  if (job.isError) return <ErrorState message={job.error.message} onRetry={() => void job.refetch()} />;
  if (cv.isError) return <ErrorState message={cv.error.message} onRetry={() => void cv.refetch()} />;
  const result = job.data.result;
  if (!result || !jobId) return <ErrorState title="Nothing to review yet" message="Tailoring hasn't produced a result. Go back and run it again." />;

  const edits = result.edits;
  const undecided = edits.filter((e) => !decisions[e.block_id]);
  const accepted = edits.filter((e) => decisions[e.block_id]?.status === "accepted").length;
  const rejected = edits.filter((e) => decisions[e.block_id]?.status === "rejected").length;

  const acceptAll = () => {
    decideMany(jobId, Object.fromEntries(undecided.map((e) => [e.block_id, { status: "accepted" as const }])));
    setConfirm(false);
  };

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <div className="summary">
        <div className="sum"><b>{Math.round(result.match.score)}%</b><span>Match before tailoring</span></div>
        <div className="sum"><b>{edits.length}</b><span>{edits.length === 1 ? "Suggested change" : "Suggested changes"}</span></div>
        <div className="sum"><b>{result.dropped.length}</b><span>Removed by Truth Check</span></div>
        <div className="sum"><b>{result.match.gaps}</b><span>{result.match.gaps === 1 ? "Gap left as it is" : "Gaps left as they are"}</span></div>
      </div>
      <Alert tone="info" title="Your original CV stays unchanged">
        Nothing is applied until you accept it. An updated match score isn't calculated yet, so none is shown.
      </Alert>
      <TruthCheck kept={edits.length} dropped={result.dropped} />

      {edits.length === 0 ? (
        <Card><EmptyState icon="shieldCheck" title="No safe improvements found">
          ShortlistMe couldn't find changes that stay faithful to your CV. That's a fine outcome — your CV already says what it can.
        </EmptyState></Card>
      ) : (
        <>
          <div className="review-bar">
            <span><b>{accepted + rejected}</b> of {edits.length} reviewed · {accepted} accepted · {rejected} rejected</span>
            <Button size="sm" variant="primary" icon="check" disabled={undecided.length === 0} onClick={() => setConfirm(true)}>
              Accept all safe changes{undecided.length > 0 ? ` (${undecided.length})` : ""}
            </Button>
          </div>
          {edits.map((e) => (
            <EditCard key={e.block_id} edit={e} block={blocks.get(e.block_id)} decision={decisions[e.block_id]} onDecide={(d) => decide(jobId, e.block_id, d)} />
          ))}
        </>
      )}
      <RemovedList dropped={result.dropped} blocks={blocks} />

      <div className="flow-nav">
        <span className="muted" style={{ alignSelf: "center", fontSize: "var(--fs-sm)" }}>Decisions are saved on this device.</span>
        <Button variant="primary" size="lg" iconRight="arrowRight" onClick={onNext}>Continue to export</Button>
      </div>

      <Modal open={confirm} title={`Accept ${plural(undecided.length, "change")}?`} onClose={() => setConfirm(false)}
        footer={<><Button variant="ghost" onClick={() => setConfirm(false)}>Cancel</Button><Button variant="primary" onClick={acceptAll}>Accept {undecided.length}</Button></>}>
        <p>Each of these passed Truth Check, but it can't guarantee every detail is right. You can still reject or edit any change afterwards.</p>
      </Modal>
    </div>
  );
}

/* ---------- step 5: export ---------- */
function StepExport() {
  const { state } = useWorkspace();
  const { jobId } = state.current;
  const job = useQuery({ queryKey: ["job", jobId], queryFn: () => getTailoring(jobId!), enabled: !!jobId, staleTime: Infinity });
  const [copied, setCopied] = useState<"idle" | "ok" | "fail">("idle");
  const decisions = (jobId && state.decisions[jobId]) || {};
  const edits = job.data?.result?.edits ?? [];
  const accepted = edits.filter((e) => decisions[e.block_id]?.status === "accepted");

  const dl = useMutation({
    mutationFn: async (format: "docx" | "pdf") => {
      const finalEdits = Object.fromEntries(accepted.map((e) => [e.block_id, decisions[e.block_id]?.text ?? e.new_text]));
      const { blob, filename } = await exportCV(state.current.cvId!, format, finalEdits);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    },
  });

  const copy = async () => {
    const body = accepted.map((e) => decisions[e.block_id]?.text ?? e.new_text).join("\n\n");
    try { await navigator.clipboard.writeText(body); setCopied("ok"); } catch { setCopied("fail"); }
  };

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <Card>
        <CardHead title="Your tailored CV" subtitle={`${plural(accepted.length, "accepted change")} out of ${edits.length}.`} />
        <div className="export-grid">
          <div className="sum"><b>{accepted.length}</b><span>Accepted</span></div>
          <div className="sum"><b>{edits.filter((e) => decisions[e.block_id]?.status === "rejected").length}</b><span>Rejected — original kept</span></div>
        </div>
      </Card>
      <Card>
        <CardHead title="Export" subtitle="Download a finished document with your accepted changes applied." />
        <div className="export-actions">
          <Button variant="primary" icon="download" disabled={dl.isPending} onClick={() => dl.mutate("docx")}>{dl.isPending && dl.variables === "docx" ? "Preparing…" : "Download DOCX"}</Button>
          <Button icon="download" disabled={dl.isPending} onClick={() => dl.mutate("pdf")}>{dl.isPending && dl.variables === "pdf" ? "Preparing…" : "Download PDF"}</Button>
        </div>
        {dl.isError && <Alert tone="danger">{dl.error.message}</Alert>}
        <p className="muted" style={{ marginTop: 14, fontSize: "var(--fs-sm)" }}>Your original CV file is untouched — the download is a new copy with only your accepted changes applied, DOCX keeps your original formatting; the PDF is a clean one-page re-layout of the same text. Open it and read it through before you send it.</p>
        <div className="export-actions" style={{ marginTop: 14 }}>
          <Button icon="file" disabled={accepted.length === 0} onClick={() => void copy()}>Copy accepted changes</Button>
          <span role="status" className="muted" style={{ fontSize: "var(--fs-sm)" }}>
            {copied === "ok" && "Copied."}{copied === "fail" && "Couldn't copy — your browser blocked clipboard access."}
          </span>
        </div>
      </Card>
    </div>
  );
}

/* ---------- page ---------- */
export default function Tailor() {
  const { state, setCurrent, resetCurrent } = useWorkspace();
  const { cvId, jdId, jobId } = state.current;
  const step = !cvId ? 0 : !jdId ? Math.min(state.current.step, 1) : !jobId ? Math.min(state.current.step, 3) : state.current.step;
  const to = (n: number) => setCurrent({ step: n });
  const usage = useUsage();

  return (
    <>
      <PageHeader title="Tailor your CV" subtitle="Match your CV to a role, review every change, and keep your real experience intact."
        action={(cvId || jdId) && <Button variant="ghost" icon="refresh" onClick={resetCurrent}>Start over</Button>} />
      {usage.data && <p className="muted" role="status" style={{ margin: "-4px 0 12px" }}>{usageLine(usage.data)}</p>}
      <ProgressStepper current={step} onNavigate={to} />
      <div key={step} className="rise" style={{ display: "grid", gap: 20 }}>
        {step === 0 && <StepCV onNext={() => to(1)} />}
        {step === 1 && <StepJD onNext={() => to(2)} />}
        {step === 2 && <StepMatch onNext={() => setCurrent({ jobId: null, step: 3 })} />}
        {step === 3 && <StepRun onDone={() => to(4)} />}
        {step === 4 && <StepReview onNext={() => to(5)} />}
        {step === 5 && <StepExport />}
      </div>
    </>
  );
}
