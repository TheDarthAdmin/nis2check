"use client";

import { useRouter } from "next/navigation";
import { runLabel } from "@/lib/findings";
import { HostedRun } from "@/lib/types";

export function RunSwitcher({ runs, currentId }: { runs: HostedRun[]; currentId: string }) {
  const router = useRouter();
  if (runs.length < 2) return null;
  return (
    <label className="run-switcher">
      <span className="muted">Run</span>
      <select className="field" value={currentId} onChange={(event) => router.push(`/runs/${event.target.value}`)}>
        {runs.map((run) => <option key={run.id} value={run.id}>{runLabel(run)}{run.status === "COMPLETE" ? "" : ` · ${run.status.toLowerCase()}`}</option>)}
      </select>
    </label>
  );
}
