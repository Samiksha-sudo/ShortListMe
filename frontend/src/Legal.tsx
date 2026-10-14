import type { ReactNode } from "react";
import { Logo } from "./ui/AppShell";

export const SUPPORT_EMAIL = "kadsamiksha347@gmail.com";
const UPDATED = "14 October 2026";

export type LegalPage = "privacy" | "terms";

export const readLegalPage = (): LegalPage | null => {
  const h = window.location.hash.replace(/^#\/?/, "");
  return h === "privacy" || h === "terms" ? h : null;
};

export function LegalLinks() {
  return (
    <span className="legal-links">
      <a href="#/privacy">Privacy Policy</a> · <a href="#/terms">Terms</a>
    </span>
  );
}

const Section = ({ title, children }: { title: string; children: ReactNode }) => (
  <section style={{ marginBottom: 24 }}><h2 style={{ fontSize: 20, margin: "0 0 8px" }}>{title}</h2>{children}</section>
);

function Privacy() {
  return (
    <>
      <h1>Privacy Policy</h1>
      <p>Last updated {UPDATED}. ShortlistMe is run by Samiksha Kad in the United Kingdom ("we"). We are the controller of your personal data. Contact: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.</p>
      <Section title="What we collect">
        <ul>
          <li><b>Account data:</b> your email address and a hashed (never plain-text) password.</li>
          <li><b>CVs you upload</b> and the text extracted from them, which usually includes your name, contact details, work history and education.</li>
          <li><b>Job descriptions</b> you paste in, and the tailoring results we generate.</li>
          <li><b>Billing data:</b> if you subscribe, Stripe handles your card details. We store only a Stripe customer ID and your subscription status. We never see or store your card number.</li>
        </ul>
      </Section>
      <Section title="Why we use it">
        <p>To provide the service you asked for: tailoring your CV to a job description, exporting it, and running your account and subscription (legal basis: performing our contract with you). We also keep basic security logs to prevent abuse (legitimate interests).</p>
      </Section>
      <Section title="Who we share it with">
        <ul>
          <li><b>Google (Gemini AI):</b> the text of your CV and the job description is sent to Google's Gemini API to generate suggestions.</li>
          <li><b>Stripe:</b> payments and subscriptions.</li>
          <li><b>Our hosting and email providers:</b> to run the site and send account emails (such as password resets).</li>
        </ul>
        <p>We do not sell your data or use it for advertising.</p>
      </Section>
      <Section title="How long we keep it">
        <p>Until you delete your account. Deleting your account from Settings erases your profile, CVs, job descriptions and tailoring results from our systems and cancels your subscription. Records Stripe must keep for tax and accounting law are held by Stripe under its own policy.</p>
      </Section>
      <Section title="Your rights">
        <p>Under UK GDPR you can access, correct, export or erase your data, and object to or restrict how we use it. You can delete your account yourself in Settings, or email us for anything else. If you are unhappy with our response you can complain to the Information Commissioner's Office (ico.org.uk).</p>
      </Section>
      <Section title="Storage on your device">
        <p>We use your browser's local storage to keep you signed in and to remember your CV and application list on that device. We do not use advertising or tracking cookies.</p>
      </Section>
    </>
  );
}

function Terms() {
  return (
    <>
      <h1>Terms of Service</h1>
      <p>Last updated {UPDATED}. By creating an account you agree to these terms.</p>
      <Section title="The service">
        <p>ShortlistMe uses AI to suggest edits that tailor your CV to a job description. Suggestions are only suggestions: you are responsible for checking that your final CV is accurate and truthful before you send it to anyone. We do not guarantee interviews or job offers.</p>
      </Section>
      <Section title="Plans and payment">
        <ul>
          <li>Every account includes 5 free tailorings.</li>
          <li><b>Pro costs £20 per month</b>, includes up to 50 tailorings per month, and <b>renews automatically each month</b> until you cancel.</li>
          <li><b>Cancel any time</b> from Settings → Manage subscription. You keep Pro until the end of the period you have paid for, and you will not be charged again.</li>
          <li><b>Refunds:</b> you have 14 days from first subscribing to ask for a refund if you have not used the paid tailorings. Email {SUPPORT_EMAIL}. Otherwise payments for a period already started are not refunded.</li>
        </ul>
      </Section>
      <Section title="Your content">
        <p>You keep ownership of your CV and job descriptions. You give us permission to process them, including sending them to our AI provider, solely to provide the service. Only upload content you have the right to use.</p>
      </Section>
      <Section title="Acceptable use">
        <p>Do not misuse the service, attempt to break or overload it, or use it to produce false or misleading information.</p>
      </Section>
      <Section title="Liability">
        <p>The service is provided "as is". To the extent the law allows, we are not liable for indirect losses, including lost job opportunities. Nothing here limits liability that cannot legally be limited, or your statutory consumer rights.</p>
      </Section>
      <Section title="Changes and contact">
        <p>We may update these terms and will tell you about material changes. Questions: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>. These terms are governed by the laws of England and Wales.</p>
      </Section>
    </>
  );
}

export default function Legal({ page }: { page: LegalPage }) {
  const back = () => { window.location.hash = ""; };
  return (
    <div style={{ minHeight: "100vh", padding: "32px 20px 60px" }}>
      <div style={{ maxWidth: 760, margin: "0 auto", lineHeight: 1.65 }}>
        <p><a href="#/" onClick={back}><Logo /></a></p>
        {page === "privacy" ? <Privacy /> : <Terms />}
        <p><a href="#/" onClick={back}>← Back</a></p>
      </div>
    </div>
  );
}
