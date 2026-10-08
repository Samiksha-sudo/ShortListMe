import type { ReactNode } from "react";
import Icon from "./ui/Icon";
import { Logo, SiteFooter } from "./ui/AppShell";

/** Split-screen auth layout: focused form on the left, product promise on the right (hidden on small screens). */
export default function AuthLayout({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="auth">
      <main className="auth-form-side">
        <div className="auth-card rise">
          <Logo />
          <h1>{title}</h1>
          {subtitle && <p className="sub">{subtitle}</p>}
          {children}
        </div>
        <SiteFooter />
      </main>
      <aside className="auth-brand-side" aria-label="About ShortlistMe">
        <h2>Tailor your CV to the role — without inventing experience.</h2>
        <p>Other AI tools rewrite your CV. ShortlistMe shows what changed, why it changed, and checks that the AI didn't invent experience.</p>
        <ul className="auth-points">
          <li><Icon name="target" />See how well your CV matches a role, and where the real gaps are.</li>
          <li><Icon name="eye" />Review every suggested change before it is applied.</li>
          <li><Icon name="shieldCheck" />Protected facts such as employers and dates cannot be rewritten.</li>
        </ul>
        <div className="auth-demo" aria-hidden="true">
          <div className="eyebrow" style={{ color: "#9aa2d6", marginBottom: 6 }}>Example change</div>
          <div className="diff-line">
            Built a reporting tool <span className="diff-del">for the team</span>{" "}
            <span className="diff-add">used by 12 analysts to track hiring pipelines</span>
          </div>
        </div>
      </aside>
    </div>
  );
}
