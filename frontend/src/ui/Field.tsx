import { useId, useState, type InputHTMLAttributes } from "react";
import Icon from "./Icon";

interface FieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  label: string;
  hint?: string;
  error?: string;
}

/** Labelled input with hint/error wired up through aria-describedby. Password fields get a show/hide toggle. */
export default function Field({ label, hint, error, type = "text", ...rest }: FieldProps) {
  const id = useId();
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  const describedBy = error ? `${id}-err` : hint ? `${id}-hint` : undefined;

  return (
    <div className={`field${error ? " invalid" : ""}`}>
      <label htmlFor={id}>{label}</label>
      <div className="input-wrap">
        <input id={id} className="input" type={isPassword && show ? "text" : type}
          aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...rest} />
        {isPassword && (
          <button type="button" className="btn btn-ghost btn-sm" aria-pressed={show}
            aria-label={show ? "Hide password" : "Show password"} onClick={() => setShow((s) => !s)}>
            <Icon name={show ? "eyeOff" : "eye"} />
          </button>
        )}
      </div>
      {error ? <span id={`${id}-err`} className="error" role="alert">{error}</span>
        : hint ? <span id={`${id}-hint`} className="hint">{hint}</span> : null}
    </div>
  );
}
