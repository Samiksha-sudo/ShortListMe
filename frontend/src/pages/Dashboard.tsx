import { useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";
import { deleteAccount } from "../api";
import { firstName, formatBytes, greeting, matchBand, plural, timeAgo } from "../lib/format";
import { go } from "../lib/route";
import { appStatus, useWorkspace, type AppRecord } from "../lib/store";
import { PlanCard, PlanSummary } from "../ui/Billing";
import { PageHeader } from "../ui/AppShell";
import Icon, { type IconName } from "../ui/Icon";
import { Badge, Button, Card, CardHead, EmptyState, StatusBadge } from "../ui/primitives";

/** Open an application in the Tailor workflow at the stage it reached. */
function useOpenApp() {
  const { setCurrent } = useWorkspace();
  return (a: AppRecord, step?: number) => {
    const natural = a.stage === "tailored" ? 4 : a.stage === "analysed" ? 2 : 1;
    setCurrent({ cvId: a.cvId, jdId: a.jdId, jobId: a.jobId, step: step ?? natural });
    go("tailor");
  };
}

export function ApplicationRow({ app }: { app: AppRecord }) {
  const open = useOpenApp();
  const status = appStatus(app);
  const band = app.score !== null ? matchBand(app.score) : null;
  const title = app.role ?? "Untitled role";
  return (
    <li className="app-row">
      <div style={{ minWidth: 0 }}>
        <div className="app-title">{title}{app.company && <span className="muted" style={{ fontWeight: 400 }}> · {app.company}</span>}</div>
        <div className="app-sub">Updated {timeAgo(app.at)}{app.cvName && ` · ${app.cvName}`}</div>
      </div>
      <div className="app-score">
        {app.score !== null && band ? <>
          <span>{Math.round(app.score)}%</span><span className="muted" style={{ fontWeight: 500, fontSize: "var(--fs-xs)" }}>{band.label}</span>
        </> : <span className="muted" style={{ fontWeight: 500 }}>Not scored</span>}
      </div>
      <StatusBadge status={status} />
      <div className="app-actions">
        <Button size="sm" onClick={() => open(app)}>{status === "Needs review" || status === "Tailored" ? "Review" : status === "Ready" ? "Open" : "Continue"}</Button>
      </div>
    </li>
  );
}

export function ApplicationList({ apps }: { apps: AppRecord[] }) {
  return <ul className="app-list">{apps.map((a) => <ApplicationRow key={a.id} app={a} />)}</ul>;
}

function Metric({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return <Card className="metric"><div className="metric-label">{label}</div><div className="metric-value">{value}</div>{note && <div className="metric-note">{note}</div>}</Card>;
}

export default function Dashboard({ email }: { email: string }) {
  const { state, setCurrent } = useWorkspace();
  const name = firstName(email);
  const { cvs, apps } = state;

  const analysed = apps.filter((a) => a.stage !== "draft").length;
  const tailored = apps.filter((a) => a.stage === "tailored").length;
  const scores = apps.map((a) => a.score).filter((s): s is number => s !== null);
  const avg = scores.length ? Math.round(scores.reduce((x, y) => x + y, 0) / scores.length) : null;
  const reviewed = apps.some((a) => a.accepted + a.rejected > 0);
  const recent = [...apps].sort((a, b) => b.at - a.at).slice(0, 5);

  const steps = [
    { label: "Upload your CV", done: cvs.length > 0 },
    { label: "Add a job description", done: apps.length > 0 },
    { label: "Analyse the role", done: analysed > 0 },
    { label: "Check your match score", done: scores.length > 0 },
    { label: "Tailor your CV", done: tailored > 0 },
    { label: "Review the suggested changes", done: reviewed },
  ];
  const doneCount = steps.filter((s) => s.done).length;
  const nextIdx = steps.findIndex((s) => !s.done);

  const startNew = () => { setCurrent({ cvId: cvs[0]?.id ?? null, jdId: null, jobId: null, step: cvs[0] ? 1 : 0 }); go("tailor"); };
  const quick: { icon: IconName; title: string; note: string; run: () => void }[] = [
    { icon: "sparkles", title: "Tailor a CV", note: "Match your CV to a new role", run: startNew },
    { icon: "upload", title: "Upload a CV", note: "Add another version", run: () => { setCurrent({ cvId: null, jdId: null, jobId: null, step: 0 }); go("tailor"); } },
    { icon: "list", title: "View applications", note: "Pick up where you left off", run: () => go("applications") },
  ];

  return (
    <>
      <section className="hero rise" aria-labelledby="hello">
        <div>
          <h1 id="hello">{greeting()}{name ? `, ${name}` : ""}</h1>
          <p>Ready to strengthen your next application?</p>
        </div>
        <Button variant="primary" size="lg" icon="sparkles" onClick={startNew}>Tailor a CV</Button>
      </section>

      <section className="metrics" aria-label="Your activity on this device">
        <Metric label="CVs uploaded" value={cvs.length} />
        <Metric label="Jobs analysed" value={analysed} />
        <Metric label="CVs tailored" value={tailored} />
        <Metric label="Average match" value={avg === null ? "—" : `${avg}%`} note={avg === null ? "Appears after your first match" : undefined} />
      </section>

      <div className="dash-grid">
        <Card>
          <CardHead title="Recent applications" subtitle="Saved on this device."
            action={apps.length > 0 ? <Button size="sm" variant="ghost" iconRight="arrowRight" onClick={() => go("applications")}>View all</Button> : undefined} />
          {recent.length === 0 ? (
            <EmptyState icon="briefcase" title="No applications yet" compact action={<Button variant="primary" onClick={startNew}>Tailor your first CV</Button>}>
              Upload a CV and paste a job description. Your progress will show up here.
            </EmptyState>
          ) : <ApplicationList apps={recent} />}
        </Card>

        <div className="stack">
          <PlanSummary />
          <Card>
            <CardHead title="Quick actions" />
            <div className="quick">
              {quick.map((q) => (
                <button key={q.title} type="button" onClick={q.run}>
                  <span className="q-ico"><Icon name={q.icon} /></span>
                  <span>{q.title}<small>{q.note}</small></span>
                </button>
              ))}
            </div>
          </Card>
          <Card>
            <CardHead title="Getting started" subtitle={`${doneCount} of ${steps.length} done`} />
            <div className="progress-bar" role="progressbar" aria-valuemin={0} aria-valuemax={steps.length} aria-valuenow={doneCount} aria-label="Getting started progress">
              <i style={{ width: `${(doneCount / steps.length) * 100}%` }} />
            </div>
            <ul className="checklist">
              {steps.map((s, i) => (
                <li key={s.label} className={s.done ? "done" : i === nextIdx ? "next" : ""}>
                  <span className="check-dot" aria-hidden="true">{s.done ? <Icon name="check" /> : i + 1}</span>
                  <span className="t">{s.label}</span>
                  <span className="sr-only">{s.done ? "(done)" : i === nextIdx ? "(next)" : ""}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}

/* ---------- Applications ---------- */
export function Applications() {
  const { state, setCurrent } = useWorkspace();
  const apps = [...state.apps].sort((a, b) => b.at - a.at);
  return (
    <>
      <PageHeader title="Applications" subtitle="Every role you've worked on from this browser, and where you left off."
        action={<Button variant="primary" icon="plus" onClick={() => { setCurrent({ cvId: state.cvs[0]?.id ?? null, jdId: null, jobId: null, step: state.cvs[0] ? 1 : 0 }); go("tailor"); }}>New application</Button>} />
      <Card>
        {apps.length === 0
          ? <EmptyState icon="list" title="No applications yet" action={<Button variant="primary" onClick={() => go("tailor")}>Start tailoring</Button>}>
              When you analyse or tailor against a job, it's saved here on this device.
            </EmptyState>
          : <ApplicationList apps={apps} />}
      </Card>
      <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>This list is stored in this browser. Another device or browser won't show it.</p>
    </>
  );
}

/* ---------- My CVs ---------- */
export function MyCVs() {
  const { state, setCurrent } = useWorkspace();
  return (
    <>
      <PageHeader title="My CVs" subtitle="CVs you've uploaded from this browser."
        action={<Button variant="primary" icon="upload" onClick={() => { setCurrent({ cvId: null, jdId: null, jobId: null, step: 0 }); go("tailor"); }}>Upload a CV</Button>} />
      {state.cvs.length === 0 ? (
        <Card><EmptyState icon="file" title="No CVs yet" action={<Button variant="primary" onClick={() => go("tailor")}>Upload your CV</Button>}>
          Upload a DOCX and ShortlistMe will read its sections, bullets and skills.
        </EmptyState></Card>
      ) : (
        <div className="list-grid">
          {state.cvs.map((c) => {
            const uses = state.apps.filter((a) => a.cvId === c.id).length;
            return (
              <Card key={c.id} hoverable>
                <div className="cv-row">
                  <span className="file-ico"><Icon name="file" /></span>
                  <div style={{ minWidth: 0 }}>
                    <div className="app-title">{c.filename}</div>
                    <div className="app-sub">{formatBytes(c.size)} · uploaded {timeAgo(c.at)}</div>
                  </div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
                  <Badge tone="neutral">{plural(uses, "application")}</Badge>
                  <Button size="sm" variant="primary" onClick={() => { setCurrent({ cvId: c.id, jdId: null, jobId: null, step: 1 }); go("tailor"); }}>Tailor with this CV</Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}

/* ---------- Job descriptions ---------- */
export function Jobs() {
  const { state } = useWorkspace();
  const open = useOpenApp();
  const apps = [...state.apps].sort((a, b) => b.at - a.at);
  return (
    <>
      <PageHeader title="Job Descriptions" subtitle="Roles you've pasted in from this browser." />
      {apps.length === 0 ? (
        <Card><EmptyState icon="briefcase" title="No job descriptions yet" action={<Button variant="primary" onClick={() => go("tailor")}>Add a job</Button>}>
          Paste a job description in the Tailor CV flow and it will be listed here.
        </EmptyState></Card>
      ) : (
        <div className="list-grid">
          {apps.map((a) => (
            <Card key={a.id} hoverable>
              <div className="app-title">{a.role ?? "Untitled role"}{a.company && <span className="muted" style={{ fontWeight: 400 }}> · {a.company}</span>}</div>
              <p className="muted" style={{ fontSize: "var(--fs-sm)", margin: "6px 0 14px", display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{a.jdPreview || "No preview saved."}</p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="muted" style={{ fontSize: "var(--fs-xs)" }}>{timeAgo(a.at)}</span>
                <Button size="sm" onClick={() => open(a, 1)}>Open</Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

/* ---------- Settings ---------- */
export function Settings({ email, onSignOut }: { email: string; onSignOut: () => void }) {
  const { clearAll } = useWorkspace();
  return (
    <>
      <PageHeader title="Settings" subtitle="Your account and what this browser remembers." />
      <Card>
        <CardHead title="Account" />
        <div className="settings-row"><span>Email</span><b>{email}</b></div>
        <div className="settings-row"><span>Session</span><Button onClick={onSignOut} icon="logout">Log out</Button></div>
      </Card>
      <PlanCard />
      <Card>
        <CardHead title="On this device" subtitle="Your CV list, applications and review decisions are remembered in this browser only." />
        <div className="settings-row">
          <span>Clear the saved list of CVs, applications and decisions from this browser.</span>
          <Button variant="danger" icon="trash" onClick={() => { if (window.confirm("Clear everything ShortlistMe remembers on this device? Your account is not affected.")) clearAll(); }}>Clear</Button>
        </div>
      </Card>
      <DeleteAccountCard onDeleted={() => { clearAll(); onSignOut(); }} />
    </>
  );
}

function DeleteAccountCard({ onDeleted }: { onDeleted: () => void }) {
  const [password, setPassword] = useState("");
  const [open, setOpen] = useState(false);
  const mutation = useMutation({ mutationFn: () => deleteAccount(password), onSuccess: onDeleted });
  return (
    <Card>
      <CardHead title="Delete account" subtitle="Permanently erase your account, CVs, job descriptions and results, and cancel any subscription. This cannot be undone." />
      {!open ? (
        <div className="settings-row"><span>Your data is removed from our systems straight away.</span><Button variant="danger" icon="trash" onClick={() => setOpen(true)}>Delete account</Button></div>
      ) : (
        <form className="settings-row" onSubmit={(e) => { e.preventDefault(); if (password) mutation.mutate(); }}>
          <input type="password" autoComplete="current-password" placeholder="Confirm with your password" value={password}
            onChange={(e) => setPassword(e.target.value)} style={{ flex: 1, minWidth: 0 }} />
          <Button type="submit" variant="danger" loading={mutation.isPending}>Permanently delete</Button>
          {mutation.isError && <span role="alert" style={{ color: "var(--danger, #ff6b57)" }}>{mutation.error.message}</span>}
        </form>
      )}
    </Card>
  );
}
