import { useQuery } from "@tanstack/react-query";
import { getHealth } from "./api";
import UploadCV from "./UploadCV";

export default function App() {
  const { data, error, isLoading } = useQuery({ queryKey: ["health"], queryFn: getHealth });

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "4rem auto" }}>
      <h1>ShortlistMe</h1>
      <p>AI-tailored CVs that match the job.</p>
      <p>
        Backend:{" "}
        {isLoading ? "checking…" : error ? `unreachable (${(error as Error).message})` : data?.status}
      </p>
      <UploadCV />
    </main>
  );
}
