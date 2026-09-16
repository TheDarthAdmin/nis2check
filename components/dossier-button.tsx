"use client";

import { useState } from "react";

type Format = "pdf" | "html";

async function download(runId: string, format: Format): Promise<string | null> {
  const response = await fetch(`/api/runs/${runId}/dossier?format=${format}`);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    return typeof payload?.detail === "string" ? payload.detail : `The dossier could not be built (${response.status}).`;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] || `nis2check-dossier.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  return null;
}

/** The whole run as one document an auditor can be handed, as a PDF or as the same pages in HTML. */
export function DossierButton({ runId }: { runId: string }) {
  const [busy, setBusy] = useState<Format | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(format: Format) {
    setBusy(format);
    setError(null);
    try {
      setError(await download(runId, format));
    } catch {
      setError("The dossier could not be downloaded. Check your connection and try again.");
    } finally {
      setBusy(null);
    }
  }

  return <div className="dossier-action">
    <button className="secondary-button" type="button" disabled={busy !== null} aria-busy={busy !== null} onClick={() => run("pdf")}>
      {busy ? "Building the dossier…" : "Download dossier (PDF)"}
    </button>
    <button className="link-button" type="button" disabled={busy !== null} onClick={() => run("html")}>or HTML</button>
    {error ? <p className="error-text" role="alert">{error}</p> : null}
  </div>;
}
