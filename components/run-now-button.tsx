"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function RunNowButton() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "running">("idle");
  const [error, setError] = useState<string | null>(null);
  async function run() {
    setError(null);
    setStatus("running");
    const response = await fetch("/api/runs", { method: "POST" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
      setError(typeof body?.detail === "string" ? body.detail : "The collection could not start. Please try again.");
      setStatus("idle");
      return;
    }
    router.refresh();
    setStatus("idle");
  }
  return <div className="run-action"><button className="primary-button" type="button" disabled={status === "running"} onClick={run}>{status === "running" ? "Collecting evidence…" : "Run collection now"}</button>{error ? <p className="error-text" role="alert">{error}</p> : null}</div>;
}
