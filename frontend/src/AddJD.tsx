import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { saveJD } from "./api";

// Keep in step with MIN_CHARS / MAX_CHARS in backend/app/api/jds.py.
const MIN_CHARS = 100;
const MAX_CHARS = 20_000;

export default function AddJD({ onSaved }: { onSaved?: (jdId: string) => void }) {
  const [text, setText] = useState("");
  const save = useMutation({ mutationFn: saveJD, onSuccess: (d) => onSaved?.(d.jd_id) });

  const length = text.trim().length;
  const tooShort = length < MIN_CHARS;
  const tooLong = length > MAX_CHARS;

  return (
    <section>
      <h2>Add the job description</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!tooShort && !tooLong) save.mutate(text);
        }}
      >
        <textarea
          className="jd-text"
          rows={10}
          value={text}
          onChange={(e) => { setText(e.target.value); if (save.isSuccess || save.isError) save.reset(); }}
          placeholder="Paste the full job description here"
          aria-label="Job description"
        />
        <p className={`hint${length > 0 && (tooShort || tooLong) ? " invalid" : ""}`}>
          {tooLong
            ? `Too long: ${length.toLocaleString()} of ${MAX_CHARS.toLocaleString()} characters.`
            : length > 0 && tooShort
              ? `Add ${MIN_CHARS - length} more characters (minimum ${MIN_CHARS}).`
              : `${length.toLocaleString()} characters`}
        </p>
        <button className="btn-raised" type="submit" disabled={tooShort || tooLong || save.isPending}>
          {save.isPending ? "Saving…" : "Save job description"}
        </button>
      </form>
      {save.isError && <p className="msg-error">{(save.error as Error).message}</p>}
      {save.isSuccess && (
        <div className="jd-saved">
          <p className="msg-ok">Saved · id <code>{save.data.jd_id}</code></p>
          <pre className="jd-preview">{save.data.text}</pre>
        </div>
      )}
    </section>
  );
}
