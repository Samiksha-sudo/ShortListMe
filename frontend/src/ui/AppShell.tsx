import { useEffect, useState, type ReactNode } from "react";
import { go, type Route } from "../lib/route";
import Icon, { type IconName } from "./Icon";
import { Button } from "./primitives";

const NAV: { route: Route; label: string; icon: IconName }[] = [
  { route: "dashboard", label: "Dashboard", icon: "dashboard" },
  { route: "tailor", label: "Tailor CV", icon: "sparkles" },
  { route: "applications", label: "Applications", icon: "list" },
  { route: "cvs", label: "My CVs", icon: "file" },
  { route: "jobs", label: "Job Descriptions", icon: "briefcase" },
  { route: "settings", label: "Settings", icon: "settings" },
];

export function SiteFooter() {
  return <footer className="site-footer">Design by Samiksha Kad</footer>;
}

export function Logo({ light }: { light?: boolean }) {
  return (
    <span className="brand" style={light ? undefined : { color: "var(--text-primary)" }}>
      <span className="brand-mark"><Icon name="check" /></span>ShortlistMe
    </span>
  );
}

function Sidebar({ route, email, open, onNavigate, onSignOut }: {
  route: Route; email: string; open: boolean; onNavigate: () => void; onSignOut: () => void;
}) {
  return (
    <aside className={`sidebar${open ? " open" : ""}`} aria-label="Main">
      <a className="brand" href="#/dashboard" onClick={onNavigate}>
        <span className="brand-mark"><Icon name="check" /></span>ShortlistMe
      </a>
      <nav className="nav" aria-label="Primary">
        {NAV.map((n) => (
          <a key={n.route} className="nav-link" href={`#/${n.route}`} onClick={onNavigate}
            aria-current={route === n.route ? "page" : undefined}>
            <Icon name={n.icon} />{n.label}
          </a>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className="user">
          <span className="avatar" aria-hidden="true">{email.slice(0, 1).toUpperCase()}</span>
          <div className="user-meta"><b title={email}>{email}</b><span>Signed in</span></div>
        </div>
        <button type="button" className="nav-link" onClick={onSignOut}><Icon name="logout" />Log out</button>
      </div>
    </aside>
  );
}

export default function AppShell({ route, email, onSignOut, children }: {
  route: Route; email: string; onSignOut: () => void; children: ReactNode;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => { document.getElementById("main")?.focus({ preventScroll: true }); window.scrollTo(0, 0); }, [route]);

  return (
    <div className="shell">
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <Sidebar route={route} email={email} open={open} onNavigate={() => setOpen(false)} onSignOut={onSignOut} />
      {open && <div className="scrim" onClick={() => setOpen(false)} aria-hidden="true" />}
      <div className="main">
        <header className="topbar">
          <button type="button" className="icon-btn" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            <Icon name={open ? "close" : "menu"} />
          </button>
          <Logo />
          <span style={{ marginLeft: "auto" }}>
            <Button size="sm" variant="primary" icon="sparkles" onClick={() => go("tailor")}>Tailor</Button>
          </span>
        </header>
        <main id="main" tabIndex={-1} className="content" style={{ outline: "none" }}>{children}</main>
        <SiteFooter />
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, action, crumbs }: { title: string; subtitle?: string; action?: ReactNode; crumbs?: ReactNode }) {
  return (
    <div className="page-header rise">
      <div>
        {crumbs && <div className="crumbs">{crumbs}</div>}
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action && <div className="page-actions">{action}</div>}
    </div>
  );
}
