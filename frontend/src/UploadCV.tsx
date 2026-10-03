import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadCV } from "./api";

export default function UploadCV() {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const upload = useMutation({ mutationFn: uploadCV });

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
        style={{
          border: `2px dashed ${dragging ? "#4f46e5" : "#b6bdd0"}`,
          borderRadius: 10, padding: 32, textAlign: "center", cursor: "pointer",
        }}
      >
        {upload.isPending ? "Uploading…" : "Drag a .docx here, or click to choose (max 5 MB)"}
      </div>
      <input ref={input} type="file" accept=".docx" hidden onChange={(e) => pick(e.target.files?.[0])} />
      {upload.isError && <p style={{ color: "#dc2626" }}>{(upload.error as Error).message}</p>}
      {upload.isSuccess && (
        <p style={{ color: "#16a34a" }}>
          Uploaded <b>{upload.data.filename}</b> · id <code>{upload.data.cv_id}</code>
        </p>
      )}
    </section>
  );
}
