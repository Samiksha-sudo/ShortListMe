import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadCV } from "./api";
import ParsedBlocks from "./ParsedBlocks";

export default function UploadCV({ onUploaded }: { onUploaded?: (cvId: string) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const upload = useMutation({ mutationFn: uploadCV, onSuccess: (d) => onUploaded?.(d.cv_id) });

  const pick = (file?: File) => file && upload.mutate(file);

  return (
    <section>
      <h2>Upload your CV</h2>
      <div
        role="button"
        tabIndex={0}
        onClick={() => input.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files[0]); }}
        className={`dropzone${dragging ? " dragging" : ""}`}
      >
        {upload.isPending ? "Uploading…" : "Drag a .docx here, or click to choose (max 5 MB)"}
      </div>
      <input ref={input} type="file" accept=".docx" hidden onChange={(e) => pick(e.target.files?.[0])} />
      {upload.isError && <p className="msg-error">{(upload.error as Error).message}</p>}
      {upload.isSuccess && (
        <p className="msg-ok">
          Uploaded <b>{upload.data.filename}</b> · id <code>{upload.data.cv_id}</code>
        </p>
      )}
      {upload.isSuccess && <ParsedBlocks cvId={upload.data.cv_id} />}
    </section>
  );
}
