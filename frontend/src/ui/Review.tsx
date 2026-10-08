import { useMemo, useState } from "react";
import type { Block, DroppedEdit, ProposedEdit } from "../api";
import { diffWords } from "../lib/diff";
import type { Decision } from "../lib/store";
import Icon from "./Icon";
import { Badge, Button, Card, SkillChip } from "./primitives";

/* ---------- diff ---------- */
export function DiffViewer({ before, after }: { before: string; after: string }) {
  const parts = useMemo(() => diffWords(before, after), [before, after]);
  return (
    <div className="compare">
      <div className="pane before">
        <span className="eyebrow">Original</span>
        <span>{parts.filter((p) => p.type !== "add").map((p, i) =>
          p.type === "del" ? <del key={i} className="diff-del"><span className="sr-only">removed: </span>{p.text}</del> : <span key={i}>{p.text}</span>)}</span>
      </div>
      <div className="pane after">
        <span className="eyebrow">Suggested</span>
        <span>{parts.filter((p) => p.type !== "del").map((p, i) =>
          p.type === "add" ? <ins key={i} className="diff-add"><span className="sr-only">added: </span>{p.text}</ins> : <span key={i}>{p.text}</span>)}</span>
      </div>
    </div>
  );
}

export function ValidationBadge() {
  return <Badge tone="success" icon="shieldCheck">Passed safety checks</Badge>;
}

/* ---------- Truth Check ---------- */
const CHECKS = [
  "Numbers: no new figures introduced",
  "Dates: no new dates introduced",
  "Employers and names: nothing that isn't in your CV",
  "Technologies: no tools your CV doesn't mention",
  "Seniority: your headline level is unchanged",
];

export function TruthCheck({ kept, dropped }: { kept: number; dropped: DroppedEdit[] }) {
  return (
    <div className={`truth${dropped.length ? " warn" : ""}`}>
      <div className="truth-head">
        <Icon name="shieldCheck" />Truth Check — {kept} {kept === 1 ? "suggestion" : "suggestions"} passed
        {dropped.length > 0 && `, ${dropped.length} removed`}
      </div>
      <ul>{CHECKS.map((c) => <li key={c}><Icon name="check" />{c}</li>)}</ul>
      <p className="muted" style={{ fontSize: "var(--fs-xs)", marginTop: 10 }}>
        Truth Check flags and removes changes that add unsupported details. It reduces the risk of invented experience but can't guarantee every sentence is accurate — read each change before you accept it.
      </p>
    </div>
  );
}

/* ---------- one suggestion ---------- */
export function EditCard({ edit, block, decision, onDecide }: {
  edit: ProposedEdit;
  block: Block | undefined;
  decision: Decision | undefined;
  onDecide: (d: Decision | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const before = block?.text ?? "";
  const shown = decision?.text ?? edit.new_text;
  const status = decision?.status;
  const startEdit = () => { setDraft(shown); setEditing(true); };
  const saveEdit = () => {
    const text = draft.trim();
    if (text && text !== edit.new_text) onDecide({ status: "accepted", text });
    else if (text) onDecide({ status: "accepted" });
    setEditing(false);
  };

  return (
    <Card className={`edit-card${status ? ` is-${status}` : ""}`}>
      <div className="edit-head">
        <span className="edit-where"><Icon name="file" />{block?.section ?? "CV"} · {block?.type === "bullet" ? "Bullet" : block?.type === "summary" ? "Summary" : block?.type === "headline" ? "Headline" : "Line"}</span>
        <span style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {status === "accepted" && <Badge tone="success" icon="check">{decision?.text ? "Accepted (your edit)" : "Accepted"}</Badge>}
          {status === "rejected" && <Badge tone="neutral" icon="x">Rejected — original kept</Badge>}
          {!status && <Badge tone="warning" icon="eye">Needs your decision</Badge>}
          <ValidationBadge />
        </span>
      </div>

      {editing ? (
        <div className="field" style={{ margin: 0 }}>
          <label htmlFor={`edit-${edit.block_id}`}>Edit suggested text</label>
          <textarea id={`edit-${edit.block_id}`} className="textarea" style={{ minHeight: 100 }} value={draft} onChange={(e) => setDraft(e.target.value)} />
          <span className="hint">Your own edits aren't re-checked by Truth Check, so make sure every detail is true.</span>
          <div className="edit-actions"><Button variant="primary" size="sm" onClick={saveEdit} disabled={!draft.trim()}>Save and accept</Button><Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button></div>
        </div>
      ) : (
        <DiffViewer before={before} after={shown} />
      )}

      <div className="why"><b>Why this changed</b>{edit.rationale}</div>
      {edit.added_keywords.length > 0 && (
        <div><div className="eyebrow" style={{ marginBottom: 6 }}>Matched keywords</div>
          <div className="chips">{edit.added_keywords.map((k) => <SkillChip key={k} variant="brand">{k}</SkillChip>)}</div></div>
      )}

      {!editing && (
        <div className="edit-actions">
          <Button size="sm" className={`btn-accept${status === "accepted" && !decision?.text ? " on" : ""}`} icon="check" aria-pressed={status === "accepted"}
            onClick={() => onDecide(status === "accepted" && !decision?.text ? null : { status: "accepted" })}>Accept</Button>
          <Button size="sm" className={`btn-reject${status === "rejected" ? " on" : ""}`} icon="x" aria-pressed={status === "rejected"}
            onClick={() => onDecide(status === "rejected" ? null : { status: "rejected" })}>Reject</Button>
          <Button size="sm" variant="ghost" icon="edit" onClick={startEdit}>Edit</Button>
        </div>
      )}
    </Card>
  );
}

export function RemovedList({ dropped, blocks }: { dropped: DroppedEdit[]; blocks: Map<string, Block> }) {
  if (dropped.length === 0) return null;
  return (
    <details className="details">
      <summary>{dropped.length} {dropped.length === 1 ? "suggestion was" : "suggestions were"} removed by Truth Check</summary>
      <div style={{ display: "grid", gap: 8 }}>
        {dropped.map((d) => (
          <div key={d.block_id} className="removed">
            <span style={{ fontWeight: 600 }}>{blocks.get(d.block_id)?.text.slice(0, 120) ?? "A line in your CV"}</span>
            <span>{d.reason}</span>
          </div>
        ))}
      </div>
    </details>
  );
}
