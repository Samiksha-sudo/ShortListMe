export function timeAgo(ts: number, now = Date.now()): string {
  const s = Math.max(0, Math.round((now - ts) / 1000));
  if (s < 60) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(ts).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function greeting(date = new Date()): string {
  const h = date.getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

/** A first name only when the email makes one obvious (e.g. "jane.doe@…"); never guesses otherwise. */
export function firstName(email: string): string | null {
  const local = email.split("@")[0] ?? "";
  if (!/[._-]/.test(local)) return null;
  const token = (local.split(/[._-]/)[0] ?? "").replace(/\d+/g, "");
  return token.length >= 2 ? token[0]!.toUpperCase() + token.slice(1).toLowerCase() : null;
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export type Tone = "success" | "info" | "warning" | "danger" | "neutral" | "brand";

export function matchBand(score: number): { label: string; tone: Tone } {
  if (score >= 75) return { label: "Strong match", tone: "success" };
  if (score >= 50) return { label: "Promising match", tone: "info" };
  if (score >= 30) return { label: "Partial match", tone: "warning" };
  return { label: "Early match", tone: "danger" };
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}
