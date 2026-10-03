const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export interface UploadedCV {
  cv_id: string;
  filename: string;
  size: number;
}

export async function uploadCV(file: File): Promise<UploadedCV> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/v1/cvs`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Upload failed (HTTP ${res.status})`);
  }
  return res.json();
}
