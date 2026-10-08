import { useMutation, useQuery } from "@tanstack/react-query";
import { getTailoring, startTailoring } from "./api";

const LABELS: Record<string, string> = {
  analysing: "Reading the job description",
  matching: "Matching your CV",
  rewriting: "Proposing edits",
};

export default function Tailor({ cvId, jdId }: { cvId: string; jdId: string }) {
  const start = useMutation({ mutationFn: () => startTailoring(cvId, jdId) });
  const jobId = start.data?.job_id;

  const job = useQuery({
    queryKey: ["tailoring", jobId],
    queryFn: () => getTailoring(jobId!),
    enabled: !!jobId,
    // Poll until the job finishes or fails.
    refetchInterval: (q) => (q.state.data?.status === "done" || q.state.data?.status === "failed" ? false : 1500),
  });

  const data = job.data ?? start.data;
  const running = !!data && (data.status === "queued" || data.status === "running");
  const current = data ? data.steps.indexOf(data.step) : -1;

  return (
    <section>
      <h2>Tailor my CV</h2>
      <button className="btn-raised" onClick={() => start.mutate()} disabled={start.isPending || running}>
        {running ? "Working…" : data ? "Run again" : "Tailor my CV to this job"}
      </button>
      {start.isError && <p className="msg-error">{(start.error as Error).message}</p>}
      {job.isError && <p className="msg-error">{(job.error as Error).message}</p>}
      {data && (
        <ol className="stepper">
          {data.steps.map((s, i) => {
            const state = data.status === "done" || i < current ? "done" : i === current ? (data.status === "failed" ? "failed" : "active") : "todo";
            return <li key={s} className={`step ${state}`}>{LABELS[s] ?? s}</li>;
          })}
        </ol>
      )}
      {data?.status === "failed" && <p className="msg-error">{data.error}</p>}
      {data?.status === "done" && data.result && (
        <p className="msg-ok">
          Match score {data.result.match.score}% · {data.result.match.covered} covered, {data.result.match.weak} weak,{" "}
          {data.result.match.gaps} gaps · {data.result.edits.length} edits proposed
        </p>
      )}
    </section>
  );
}
