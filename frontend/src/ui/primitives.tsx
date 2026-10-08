import { useEffect, useId, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { AppStatus } from "../lib/store";
import type { Tone } from "../lib/format";
import Icon, { type IconName } from "./Icon";

/* ---------- Button ---------- */
type Variant = "primary" | "secondary" | "ghost" | "danger";
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md" | "lg";
  block?: boolean;
  loading?: boolean;
  icon?: IconName;
  iconRight?: IconName;
}

export function Button({ variant = "secondary", size = "md", block, loading, icon, iconRight, className = "", children, disabled, type = "button", ...rest }: ButtonProps) {
  const cls = ["btn", `btn-${variant}`, size !== "md" && `btn-${size}`, block && "btn-block", className].filter(Boolean).join(" ");
  return (
    <button type={type} className={cls} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <span className="spinner" aria-hidden="true" /> : icon && <Icon name={icon} />}
      {children}
      {!loading && iconRight && <Icon name={iconRight} />}
    </button>
  );
}

/* ---------- Card ---------- */
export function Card({ children, className = "", hoverable }: { children: ReactNode; className?: string; hoverable?: boolean }) {
  return <section className={`card${hoverable ? " hoverable" : ""} ${className}`.trim()}>{children}</section>;
}

export function CardHead({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="card-head">
      <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
      {action}
    </div>
  );
}

/* ---------- Badge ---------- */
export function Badge({ tone = "neutral", icon, children }: { tone?: Tone; icon?: IconName; children: ReactNode }) {
  return <span className={`badge tone-${tone}`}>{icon && <Icon name={icon} />}{children}</span>;
}

const STATUS_TONE: Record<AppStatus, { tone: Tone; icon: IconName }> = {
  Draft: { tone: "neutral", icon: "edit" },
  Analysed: { tone: "info", icon: "target" },
  Tailored: { tone: "brand", icon: "sparkles" },
  "Needs review": { tone: "warning", icon: "eye" },
  Ready: { tone: "success", icon: "check" },
};

/** Always text + icon: colour is never the only signal. */
export function StatusBadge({ status }: { status: AppStatus }) {
  const s = STATUS_TONE[status];
  return <Badge tone={s.tone} icon={s.icon}>{status}</Badge>;
}

export function SkillChip({ children, variant }: { children: ReactNode; variant?: "brand" | "muted" }) {
  return <span className={`chip${variant ? ` is-${variant}` : ""}`}>{children}</span>;
}

/* ---------- Alerts / states ---------- */
export function Alert({ tone = "info", title, children, actions }: { tone?: Tone; title?: string; children?: ReactNode; actions?: ReactNode }) {
  const icon: IconName = tone === "danger" || tone === "warning" ? "alert" : tone === "success" ? "shieldCheck" : "info";
  return (
    <div className={`alert tone-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <Icon name={icon} />
      <div>
        {title && <div className="alert-title">{title}</div>}
        {children}
        {actions && <div className="alert-actions">{actions}</div>}
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry, title = "Something went wrong" }: { message: string; onRetry?: () => void; title?: string }) {
  return (
    <Alert tone="danger" title={title} actions={onRetry && <Button size="sm" icon="refresh" onClick={onRetry}>Try again</Button>}>
      {message}
    </Alert>
  );
}

export function EmptyState({ icon, title, children, action, compact }: { icon: IconName; title: string; children?: ReactNode; action?: ReactNode; compact?: boolean }) {
  return (
    <div className={`empty${compact ? " compact" : ""}`}>
      <div className="empty-icon"><Icon name={icon} /></div>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function Skeleton({ width = "100%", height = 14 }: { width?: string | number; height?: number }) {
  return <span className="skeleton" style={{ width, height }} aria-hidden="true" />;
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading" style={{ display: "grid", gap: 14 }}>
      {Array.from({ length: rows }, (_, i) => <Skeleton key={i} height={i % 2 ? 14 : 18} width={i % 3 === 2 ? "70%" : "100%"} />)}
    </div>
  );
}

/* ---------- Tooltip (hover + keyboard focus, described via aria) ---------- */
export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  const id = useId();
  return (
    <span className="tooltip-host" aria-describedby={id} tabIndex={0}>
      {children}
      <span role="tooltip" id={id} className="tooltip">{text}</span>
    </span>
  );
}

/* ---------- Modal (native <dialog>: focus trap, Esc, inert background) ---------- */
export function Modal({ open, title, onClose, children, footer }: { open: boolean; title: string; onClose: () => void; children: ReactNode; footer?: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  return (
    <dialog ref={ref} className="modal" aria-labelledby={titleId} onClose={onClose}
      onClick={(e) => { if (e.target === ref.current) onClose(); }}>
      <div className="modal-body">
        <h2 id={titleId}>{title}</h2>
        {children}
      </div>
      {footer && <div className="modal-foot">{footer}</div>}
    </dialog>
  );
}
