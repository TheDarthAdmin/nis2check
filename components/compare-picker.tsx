"use client";

import { useRouter } from "next/navigation";
import { runLabel } from "@/lib/findings";
import { HostedRun } from "@/lib/types";

export function ComparePicker({ runs, from, to }: { runs: HostedRun[]; from: string; to: string }) {
  const router = useRouter();
  function select(side: "from" | "to", value: string) {
    const next = side === "from" ? { from: value, to } : { from, to: value };
    router.push(`/compare?from=${next.from}&to=${next.to}`);
  }
  return <div className="compare">
    <label className="card compare-side"><span className="muted">Earlier run</span><select className="field" value={from} onChange={(event) => select("from", event.target.value)}>{runs.map((run) => <option key={run.id} value={run.id}>{runLabel(run)}</option>)}</select></label>
    <div className="arrow" aria-hidden="true">→</div>
    <label className="card compare-side"><span className="muted">Later run</span><select className="field" value={to} onChange={(event) => select("to", event.target.value)}>{runs.map((run) => <option key={run.id} value={run.id}>{runLabel(run)}</option>)}</select></label>
  </div>;
}
