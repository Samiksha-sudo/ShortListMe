import { useState } from "react";
import type { JobAnalysis, MatchItem, MatchResult, MatchStatus } from "../api";
import { matchBand, plural, type Tone } from "../lib/format";
import Icon from "./Icon";
import { Badge, Card, CardHead, SkillChip } from "./primitives";
import ScoreRing from "./ScoreRing";

export const GAP_MESSAGE =
  "ShortlistMe found this requirement in the job description, but no evidence exists in your CV. It will not be added automatically.";

const STATUS: Record<MatchStatus, { label: string; tone: Tone; icon: "check" | "alert" | "x" }> = {
  covered: { label: "Strong", tone: "success", icon: "check" },
  weak: { label: "Partial", tone: "warning", icon: "alert" },
  gap: { label: "Gap", tone: "danger", icon: "x" },
};

/* ---------- job analysis panel ---------- */
export function AnalysisPanel({ analysis }: { analysis: JobAnalysis }) {
  const seniority = analysis.seniority === "unspecified" ? "Not stated" : analysis.seniority[0]!.toUpperCase() + analysis.seniority.slice(1);
  return (
    <Card className="rise">
      <CardHead title="What this role asks for" subtitle="Read from the job description — nothing is added." />
      <div className="insight-block">
        <h3>Role</h3>
        <div style={{ fontWeight: 600, fontSize: "1.05rem" }}>{analysis.role_title || "Role not stated"}</div>
        <div className="muted" style={{ fontSize: "var(--fs-sm)" }}>Seniority: {seniority}</div>
      </div>
      {analysis.required_skills.length > 0 && (
        <div className="insight-block"><h3>Required skills</h3>
          <div className="chips">{analysis.required_skills.map((s) => <SkillChip key={s} variant="brand">{s}</SkillChip>)}</div></div>
      )}
      {analysis.nice_to_haves.length > 0 && (
        <div className="insight-block"><h3>Nice to have</h3>
          <div className="chips">{analysis.nice_to_haves.map((s) => <SkillChip key={s}>{s}</SkillChip>)}</div></div>
      )}
      {analysis.responsibilities.length > 0 && (
        <div className="insight-block"><h3>Responsibilities</h3>
          <ul className="insight-list">{analysis.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul></div>
      )}
      {analysis.ats_keywords.length > 0 && (
        <div className="insight-block"><h3>ATS keywords</h3>
          <div className="chips">{analysis.ats_keywords.map((s) => <SkillChip key={s} variant="muted">{s}</SkillChip>)}</div></div>
      )}
    </Card>
  );
}

/* ---------- match score ---------- */
export function MatchCard({ match }: { match: MatchResult }) {
  const band = matchBand(match.score);
  const total = match.items.length;
  const copy = match.gaps === 0
    ? "Your CV shows evidence for everything the role asks for."
    : `Your CV shows evidence for ${match.covered} of ${plural(total, "requirement")}. ${plural(match.gaps, "requirement")} ${match.gaps === 1 ? "has" : "have"} no evidence in your CV.`;
  return (
    <Card className="rise">
      <div className="match-hero">
        <ScoreRing score={match.score} />
        <div className="match-copy">
          <div className="eyebrow">Match Intelligence</div>
          <div className="band">{Math.round(match.score)}% {band.label}</div>
          <p>{copy}</p>
          <p className="muted" style={{ fontSize: "var(--fs-sm)" }}>Required skills count double. Partial evidence counts half.</p>
        </div>
      </div>
      <div className="breakdown">
        <div className="bd bd-brand"><i /><b>{total}</b><span>Requirements</span></div>
        <div className="bd bd-success"><i /><b>{match.covered}</b><span>Strong</span></div>
        <div className="bd bd-warning"><i /><b>{match.weak}</b><span>Partial</span></div>
        <div className="bd bd-danger"><i /><b>{match.gaps}</b><span>Gaps</span></div>
        <div className="bd bd-info"><i /><b>{match.items.filter((i) => i.kind === "must").length}</b><span>Required</span></div>
      </div>
    </Card>
  );
}

/* ---------- requirement matrix ---------- */
export function RequirementRow({ item }: { item: MatchItem }) {
  const s = STATUS[item.status];
  return (
    <tr>
      <td className="req" data-label="Requirement">
        {item.requirement}
        {item.kind === "nice" && <span className="muted" style={{ fontWeight: 400 }}> · nice to have</span>}
      </td>
      <td><Badge tone={s.tone} icon={s.icon}>{s.label}</Badge></td>
      <td className="evidence">
        {item.evidence ? <q>{item.evidence}</q> : <span className="none">No evidence in your CV</span>}
      </td>
    </tr>
  );
}

type Filter = "all" | MatchStatus;

export function RequirementMatrix({ match }: { match: MatchResult }) {
  const [filter, setFilter] = useState<Filter>("all");
  const rank: Record<MatchStatus, number> = { gap: 0, weak: 1, covered: 2 };
  const items = [...match.items].filter((i) => filter === "all" || i.status === filter).sort((a, b) => rank[a.status] - rank[b.status]);
  const filters: { key: Filter; label: string }[] = [
    { key: "all", label: `All (${match.items.length})` },
    { key: "covered", label: `Strong (${match.covered})` },
    { key: "weak", label: `Partial (${match.weak})` },
    { key: "gap", label: `Gaps (${match.gaps})` },
  ];
  return (
    <Card>
      <CardHead title="Requirement matrix" subtitle="Each requirement, and the evidence ShortlistMe found for it in your CV."
        action={<div className="filters" role="group" aria-label="Filter requirements">
          {filters.map((f) => <button key={f.key} type="button" className="filter" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>{f.label}</button>)}
        </div>} />
      {items.length === 0 ? <p className="muted">Nothing in this group.</p> : (
        <table className="matrix">
          <thead><tr><th scope="col">Requirement</th><th scope="col">Status</th><th scope="col">Evidence</th></tr></thead>
          <tbody>{items.map((i) => <RequirementRow key={`${i.kind}:${i.requirement}`} item={i} />)}</tbody>
        </table>
      )}
      {match.gaps > 0 && (
        <div className="gap-notice"><Icon name="shield" /><span>{GAP_MESSAGE}</span></div>
      )}
    </Card>
  );
}

/* ---------- gap coaching ---------- */
export function GapCoaching({ match }: { match: MatchResult }) {
  const gaps = match.items.filter((i) => i.status === "gap");
  if (gaps.length === 0) return null;
  return (
    <Card>
      <CardHead title="Gap coaching" subtitle="Honest next steps for requirements your CV doesn't evidence yet." />
      <div style={{ display: "grid", gap: 12 }}>
        {gaps.map((g) => (
          <div key={g.requirement} className="gap-card">
            <h3>{g.requirement}</h3>
            <p>Your CV doesn't show this yet. If you genuinely have this experience, add it to your CV yourself and run the match again. Otherwise, mention your willingness to learn, or leave it out.</p>
            <p className="warn">Do not add this unless you genuinely have this experience.</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
