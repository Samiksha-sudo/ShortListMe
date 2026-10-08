import { useEffect, useState } from "react";
import { matchBand } from "../lib/format";

/** Animated score ring. The number is always shown as text, so it never relies on colour alone. */
export default function ScoreRing({ score, size = 148, label = "match score" }: { score: number; size?: number; label?: string }) {
  const stroke = Math.round(size * 0.085);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [shown, setShown] = useState(0);
  const { tone } = matchBand(score);

  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(score));
    return () => cancelAnimationFrame(id);
  }, [score]);

  return (
    <div className="ring" style={{ width: size, height: size }} role="img" aria-label={`${score} percent ${label}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle className="ring-track" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} />
        <circle className={`ring-value stroke-${tone === "neutral" || tone === "brand" ? "info" : tone}`} cx={size / 2} cy={size / 2} r={r}
          fill="none" strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(100, Math.max(0, shown)) / 100)} />
      </svg>
      <div className="ring-text">
        <span className="ring-num" style={{ fontSize: size * 0.3 }}>{Math.round(score)}<small>%</small></span>
      </div>
    </div>
  );
}
