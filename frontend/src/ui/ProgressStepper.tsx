import Icon from "./Icon";

export const FLOW_STEPS = ["CV", "Job", "Analysis", "Tailoring", "Review", "Export"] as const;

/** Guided-workflow stepper. Completed steps are clickable (go back); future steps are not. */
export default function ProgressStepper({ current, onNavigate }: { current: number; onNavigate: (step: number) => void }) {
  return (
    <nav aria-label="Tailoring progress">
      <ol className="stepper">
        {FLOW_STEPS.map((label, i) => {
          const state = i < current ? "done" : i === current ? "current" : "todo";
          return (
            <li key={label} className={`step-${state}`}>
              <button type="button" className="step-btn" disabled={i >= current}
                aria-current={state === "current" ? "step" : undefined} onClick={() => onNavigate(i)}>
                <span className="step-dot">{state === "done" ? <Icon name="check" /> : i + 1}</span>
                <span className="step-label">{label}<span className="sr-only">{state === "done" ? " (completed)" : state === "current" ? " (current step)" : ""}</span></span>
              </button>
              {i < FLOW_STEPS.length - 1 && <span className="step-line" aria-hidden="true"><i /></span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
