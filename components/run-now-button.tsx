"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

function elapsed(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function RunNowButton({ busy = false }: { busy?: boolean }) {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "running">("idle");
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);
  const running = busy || status === "running";

  useEffect(() => {
    if (status !== "running") return;
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, [status]);

  async function run() {
    setError(null);
    setSeconds(0);
    setStatus("running");
    try {
      const response = await fetch("/api/runs", { method: "POST" });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
        setError(typeof body?.detail === "string" ? body.detail : "The collection could not start. Please try again.");
        return;
      }
      router.refresh();
    } catch {
      setError("The collection service could not be reached. Check your connection and try again.");
    } finally {
      setStatus("idle");
    }
  }

  return <div className="run-action">
    <button className="primary-button" type="button" disabled={running} aria-busy={running} onClick={run}>{running ? "Collecting evidence…" : "Run collection now"}</button>
    {status === "running" ? <p className="muted run-progress" role="status">Reading your tenant read-only. This usually takes a few minutes — {elapsed(seconds)} so far.</p> : null}
    {error ? <p className="error-text" role="alert">{error}</p> : null}
  </div>;
}
