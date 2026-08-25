"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function RunNowButton() {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "running" | "error">("idle");
  async function run() {
    setStatus("running");
    const response = await fetch("/api/runs", { method: "POST" });
    if (!response.ok) return setStatus("error");
    router.refresh();
    setStatus("idle");
  }
  return <div className="run-action"><button className="primary-button" type="button" disabled={status === "running"} onClick={run}>{status === "running" ? "Collecting evidence…" : "Run collection now"}</button>{status === "error" ? <p className="error-text">The collection could not start. Check the hosted service configuration and Graph consent.</p> : null}</div>;
}
