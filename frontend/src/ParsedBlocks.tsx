import { useQuery } from "@tanstack/react-query";
import { getCV, type Block } from "./api";

function BlockRow({ block }: { block: Block }) {
  const isHeadline = block.type === "headline";
  const indent = block.type === "bullet" ? 20 : 0;
  return (
    <li
      style={{
        display: "flex", gap: 8, padding: "4px 0", marginLeft: indent, listStyle: "none",
        background: isHeadline ? "#e3f8ef" : undefined,
      }}
    >
      <span
        title={block.editable ? "Editable" : "Locked"}
        aria-label={block.editable ? "editable" : "locked"}
        style={{ width: 20, flexShrink: 0 }}
      >
        {block.editable ? (isHeadline ? "✏️" : "") : "🔒"}
      </span>
      <span style={{ fontWeight: block.type === "role_title" || block.type === "name" ? 600 : 400 }}>
        {block.text}
        {isHeadline && <em style={{ color: "#0ccf86", marginLeft: 8 }}>headline · editable</em>}
      </span>
    </li>
  );
}

export default function ParsedBlocks({ cvId }: { cvId: string }) {
  const { data, error, isLoading } = useQuery({ queryKey: ["cv", cvId], queryFn: () => getCV(cvId) });

  if (isLoading) return <p>Reading your CV…</p>;
  if (error) return <p style={{ color: "#dc2626" }}>{(error as Error).message}</p>;
  if (!data) return null;

  const groups = data.sections.map((name) => ({
    name,
    blocks: data.blocks.filter((b) => b.section === name && b.type !== "heading"),
  }));

  return (
    <div style={{ marginTop: 24 }}>
      <h2>Parsed CV</h2>
      <p style={{ color: "#555" }}>🔒 locked blocks are never changed. Everything else may be tailored.</p>
      {groups.filter((g) => g.blocks.length).map((g) => (
        <section key={g.name} style={{ marginBottom: 16 }}>
          <h3 style={{ borderBottom: "1px solid #e5e7eb", paddingBottom: 4 }}>{g.name}</h3>
          <ul style={{ padding: 0, margin: 0 }}>
            {g.blocks.map((b) => <BlockRow key={b.id} block={b} />)}
          </ul>
        </section>
      ))}
    </div>
  );
}
