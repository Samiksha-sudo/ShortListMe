import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadCV, type Block, type ParsedCV, type UploadedCV } from "../api";
import { formatBytes, plural } from "../lib/format";
import Icon from "./Icon";
import type { ReactNode } from "react";
import { Badge, Card, CardHead, ErrorState, Tooltip } from "./primitives";

const MAX_BYTES = 5 * 1024 * 1024;
const DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

const STAGES = ["Uploading CV", "Reading document", "Identifying sections", "Extracting skills", "Preparing CV"];

/* ---------- drop zone + processing ---------- */
export function UploadDropzone({ onUploaded }: { onUploaded: (cv: UploadedCV) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [stage, setStage] = useState(0);
  const mutation = useMutation({ mutationFn: uploadCV, onSuccess: onUploaded });

  // The server does all of this in one request, so the stages are a read-out of elapsed work, not a percentage.
  useEffect(() => {
    if (!mutation.isPending) return;
    setStage(0);
    const id = window.setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 900);
    return () => window.clearInterval(id);
  }, [mutation.isPending]);

  const pick = (file: File | undefined) => {
    if (!file) return;
    setLocalError(null);
    if (!file.name.toLowerCase().endsWith(".docx") && file.type !== DOCX) {
      setLocalError("That file isn't a Word document. ShortlistMe reads DOCX files — save your CV as .docx and try again.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setLocalError(`That file is ${formatBytes(file.size)}. The limit is 5 MB.`);
      return;
    }
    mutation.mutate(file);
  };

  const onDrop = (e: DragEvent) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files[0]); };
  const onKey = (e: KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.current?.click(); } };

  if (mutation.isPending) {
    return (
      <Card className="processing" >
        <h2>Getting your CV ready</h2>
        <ol className="proc-list" aria-live="polite">
          {STAGES.map((s, i) => (
            <li key={s} className={i < stage ? "done" : i === stage ? "active" : ""}>
              <span className="proc-dot">{i < stage && <Icon name="check" />}</span>{s}
            </li>
          ))}
        </ol>
      </Card>
    );
  }

  const error = localError ?? (mutation.isError ? mutation.error.message : null);
  return (
    <div style={{ display: "grid", gap: 16 }}>
      {error && <ErrorState title="That upload didn't work" message={error} onRetry={() => input.current?.click()} />}
      <div className={`dropzone${dragging ? " dragging" : ""}`} role="button" tabIndex={0}
        aria-label="Upload your CV. Drop a DOCX file here or press Enter to browse."
        onClick={() => input.current?.click()} onKeyDown={onKey}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
        <div className="dz-icon"><Icon name="upload" /></div>
        <h2>Drop your CV here</h2>
        <p className="copy">or click to browse your files. ShortlistMe reads your CV and keeps your employers, dates and numbers locked.</p>
        <div className="dz-meta"><Badge tone="info" icon="file">DOCX</Badge><Badge>Up to 5 MB</Badge></div>
        <p className="dz-privacy"><Icon name="shieldCheck" />Your original CV stays unchanged.</p>
        <input ref={input} type="file" hidden accept=".docx" onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
      </div>
    </div>
  );
}

/* ---------- parsed CV preview ---------- */
const PROTECTED_TIP = "Protected facts cannot be changed by AI.";

function Line({ b }: { b: Block }) {
  const cls = b.type === "role_title" ? " role" : b.type === "bullet" ? " bullet" : "";
  return (
    <div className={`doc-line${cls}${b.editable ? " editable-line" : ""}`}>
      {!b.editable && b.type !== "bullet" && (
        <Tooltip text={PROTECTED_TIP}><span className="lock"><Icon name="lock" /><span className="sr-only">Protected. {PROTECTED_TIP}</span></span></Tooltip>
      )}
      <span>{b.text}</span>
    </div>
  );
}

export function CVPreview({ cv }: { cv: ParsedCV }) {
  const name = cv.blocks.find((b) => b.type === "name");
  const contact = cv.blocks.filter((b) => b.type === "contact");
  const sections = cv.sections.filter((s) => s !== "Header");
  const header = cv.blocks.filter((b) => b.section === "Header" && b.type !== "name" && b.type !== "contact");

  return (
    <article className="doc" aria-label="Your CV, as ShortlistMe read it">
      {name && <div className="doc-name">{name.text}</div>}
      {contact.map((c) => <div key={c.id} className="doc-contact">{c.text}</div>)}
      {header.map((b) => <Line key={b.id} b={b} />)}
      {sections.map((s) => {
        const rows = cv.blocks.filter((b) => b.section === s && b.type !== "heading");
        return (
          <section key={s} className="doc-section">
            <h3>{s}</h3>
            {rows.map((b) => <Line key={b.id} b={b} />)}
          </section>
        );
      })}
    </article>
  );
}

export function cvStats(cv: ParsedCV) {
  const editable = cv.blocks.filter((b) => b.editable).length;
  return {
    sections: cv.sections.filter((s) => s !== "Header").length,
    bullets: cv.blocks.filter((b) => b.type === "bullet").length,
    skills: cv.facts.skills.length,
    editable,
    protectedCount: cv.blocks.length - editable,
  };
}

export function CVReady({ cv, actions }: { cv: ParsedCV; actions?: ReactNode }) {
  const s = cvStats(cv);
  return (
    <div style={{ display: "grid", gap: 20 }}>
      <Card className="rise">
        <div className="ready-head">
          <div className="ready-badge"><Icon name="check" /></div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <h2>CV ready</h2>
            <p className="muted">{cv.filename}</p>
          </div>
          {actions}
        </div>
        <div className="stat-grid" style={{ marginTop: 20 }}>
          <div className="stat"><b>{s.sections}</b><span>{plural(s.sections, "section")} found</span></div>
          <div className="stat"><b>{s.bullets}</b><span>{plural(s.bullets, "bullet")}</span></div>
          <div className="stat"><b>{s.skills}</b><span>{plural(s.skills, "skill")} detected</span></div>
          <div className="stat"><b>{s.editable}<span style={{ fontWeight: 500 }}> / {s.protectedCount}</span></b><span>editable / protected lines</span></div>
        </div>
      </Card>
      <Card>
        <CardHead title="How ShortlistMe read your CV" subtitle="Check this looks right. Only highlighted lines can be reworded." />
        <div className="legend" style={{ marginBottom: 16 }}>
          <span><span className="doc-line editable-line" style={{ padding: 0 }}><span>Editable</span></span></span>
          <span><Icon name="lock" />Protected — {PROTECTED_TIP}</span>
        </div>
        <CVPreview cv={cv} />
      </Card>
    </div>
  );
}
