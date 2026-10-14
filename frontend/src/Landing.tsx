import { LegalLinks } from "./Legal";
import { useEffect, useRef } from "react";
import { Button } from "./ui/primitives";
import Icon from "./ui/Icon";

const STEPS = [
  { t: "Upload your CV", d: "A DOCX is parsed into headline, summary, roles, bullets and skills." },
  { t: "Paste the job", d: "We pull out required skills, responsibilities and ATS keywords." },
  { t: "See your match", d: "Each requirement is covered, weak or a gap, with evidence from your CV." },
  { t: "Review every change", d: "Accept, edit or reject. Export your original layout as DOCX or PDF." },
];

const PLANS = [
  { name: "Free", price: "£0", note: "5 tailorings to try it", pro: false },
  { name: "Pro", price: "£20", note: "50 tailorings every 30 days, cancel any time", pro: true },
];

const PROMISES = ["No invented numbers, tools, employers or titles", "Gaps stay gaps; we never claim skills you lack", "Your original DOCX formatting is preserved"];
const ROLES = ["Backend", "Frontend", "Full-stack", "Data"];

/** Adds the "in" class as each [data-reveal] element scrolls into view. */
function useReveal() {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const els = root.current?.querySelectorAll("[data-reveal]") ?? [];
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { threshold: 0.15 });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return root;
}

export default function Landing({ onLogin, onSignUp }: { onLogin: () => void; onSignUp: () => void }) {
  const root = useReveal();
  const jump = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  return (
    <div className="landing" ref={root}>
      <header className="land-nav">
        <b className="land-logo">shortlistme</b>
        <nav className="land-pill" aria-label="Sections">
          <a href="#how" onClick={(e) => { e.preventDefault(); jump("how"); }}>how it works</a>
          <a href="#truth" onClick={(e) => { e.preventDefault(); jump("truth"); }}>truth check</a>
          <a href="#pricing" onClick={(e) => { e.preventDefault(); jump("pricing"); }}>pricing</a>
        </nav>
        <div><Button variant="ghost" onClick={onLogin}>log in</Button> <Button className="land-white" onClick={onSignUp}>get started</Button></div>
      </header>

      <section className="land-hero">
        <span className="orb o1" /><span className="orb o2" /><span className="orb o3" />
        <h1 className="rise"><span>tailor</span><span>your</span><span>cv</span></h1>
        <p className="land-sub rise d1">repositioning your experience for every role, with nothing invented and nothing applied until you say so.</p>
        <div className="land-stat s1 rise d2">5 free<small>tailorings to start</small></div>
        <div className="land-stat s2 rise d2">100%<small>of edits truth-checked</small></div>
        <div className="land-stat s3 rise d3">DOCX<small>original format kept</small></div>
        <div className="land-verify rise d3">
          <span>ready when you are</span>
          <Button variant="primary" onClick={onSignUp}>try it free</Button>
        </div>
      </section>

      <section className="land-sec">
        <h2 data-reveal>built for every kind of role</h2>
        <div className="land-clients">
          {ROLES.map((r, i) => <div key={r} className="land-client" data-reveal style={{ transitionDelay: `${i * 80}ms` }}>{r}</div>)}
        </div>
      </section>

      <section className="land-sec" id="how">
        <h2 data-reveal>how it works</h2>
        <div className="land-grid">
          {STEPS.map((s, i) => (
            <div key={s.t} className="land-card" data-reveal style={{ transitionDelay: `${i * 90}ms` }}>
              <span className="land-num">{i + 1}</span><h3>{s.t}</h3><p>{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="land-sec" id="truth">
        <h2 data-reveal>truth check keeps it honest</h2>
        <ul className="land-list" data-reveal>
          {PROMISES.map((t) => <li key={t}><Icon name="check" /> {t}</li>)}
        </ul>
      </section>

      <section className="land-sec" id="pricing">
        <h2 data-reveal>simple pricing</h2>
        <div className="land-grid two">
          {PLANS.map((p, i) => (
            <div key={p.name} className={`land-card${p.pro ? " pro" : ""}`} data-reveal style={{ transitionDelay: `${i * 100}ms` }}>
              <h3>{p.name}</h3><div className="land-price">{p.price}{p.pro && <small>/month</small>}</div><p>{p.note}</p>
              <Button variant={p.pro ? "primary" : "secondary"} onClick={onSignUp}>{p.pro ? "get pro" : "start free"}</Button>
            </div>
          ))}
        </div>
      </section>
      <footer className="site-footer">shortlistme · <LegalLinks /></footer>
    </div>
  );
}
