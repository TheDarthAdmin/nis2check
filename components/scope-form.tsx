"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ScopingDeclaration, SectorOption } from "@/lib/types";

function number(value: string): number | null {
  const parsed = Number(value.replace(/[^0-9.]/g, ""));
  return value.trim() === "" || Number.isNaN(parsed) ? null : parsed;
}

function text(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

/**
 * Six questions, the same six the reference checkers ask, plus the balance sheet total.
 * Without it a headcount under 250 cannot prove an entity is not large, so leaving it out
 * would make the answer look more certain than it is.
 */
export function ScopeForm({ sectors, declared }: { sectors: SectorOption[]; declared: ScopingDeclaration | null }) {
  const router = useRouter();
  const [sectorKey, setSectorKey] = useState(declared?.sectorKey ?? "");
  const [employees, setEmployees] = useState(text(declared?.employees));
  const [turnover, setTurnover] = useState(text(declared?.annualTurnoverEur));
  const [balance, setBalance] = useState(text(declared?.balanceSheetTotalEur));
  const [soleProvider, setSoleProvider] = useState(declared?.soleProvider ?? false);
  const [criticalEntity, setCriticalEntity] = useState(declared?.criticalEntityCer ?? false);
  const [status, setStatus] = useState<"idle" | "saving">("idle");
  const [error, setError] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const groups = new Map<string, SectorOption[]>();
    for (const sector of sectors) {
      const label = sector.annex ? `Annex ${sector.annex} — ${sector.sector}` : sector.sector;
      groups.set(label, [...(groups.get(label) ?? []), sector]);
    }
    return [...groups.entries()];
  }, [sectors]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setStatus("saving");
    const body: Partial<ScopingDeclaration> = {
      sectorKey,
      employees: number(employees),
      annualTurnoverEur: number(turnover),
      balanceSheetTotalEur: number(balance),
      soleProvider,
      criticalEntityCer: criticalEntity,
    };
    try {
      const response = await fetch("/api/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
        setError(typeof payload?.detail === "string" ? payload.detail : "The declaration could not be saved.");
        return;
      }
      router.refresh();
    } catch {
      setError("The service could not be reached. Check your connection and try again.");
    } finally {
      setStatus("idle");
    }
  }

  return <form className="card scope-form" onSubmit={save}>
    <label className="scope-field">
      <span>Which activity describes the organisation?</span>
      <select className="field" value={sectorKey} onChange={(event) => setSectorKey(event.target.value)} required>
        <option value="" disabled>Select an activity…</option>
        {grouped.map(([label, options]) => <optgroup key={label} label={label}>
          {options.map((option) => <option key={option.key} value={option.key}>{option.subsector}</option>)}
        </optgroup>)}
      </select>
      <small className="muted">The annexes of the directive list the activities it covers. Pick the closest one.</small>
    </label>

    <div className="scope-row">
      <label className="scope-field">
        <span>Employees</span>
        <input className="field" inputMode="numeric" value={employees} onChange={(event) => setEmployees(event.target.value)} placeholder="e.g. 180" />
      </label>
      <label className="scope-field">
        <span>Annual turnover (EUR)</span>
        <input className="field" inputMode="numeric" value={turnover} onChange={(event) => setTurnover(event.target.value)} placeholder="e.g. 30000000" />
      </label>
      <label className="scope-field">
        <span>Balance sheet total (EUR)</span>
        <input className="field" inputMode="numeric" value={balance} onChange={(event) => setBalance(event.target.value)} placeholder="e.g. 25000000" />
      </label>
    </div>
    <p className="muted scope-hint">All three matter. An organisation stays medium-sized while either the turnover or the balance sheet total stays within its ceiling, so a headcount alone rarely settles it. Leave a figure blank and the answer will say so rather than guess.</p>

    <label className="check scope-check">
      <input type="checkbox" checked={soleProvider} onChange={(event) => setSoleProvider(event.target.checked)} />
      <span>We are the sole provider in this Member State of a service essential to society or the economy (article 2(2)(b)).</span>
    </label>
    <label className="check scope-check">
      <input type="checkbox" checked={criticalEntity} onChange={(event) => setCriticalEntity(event.target.checked)} />
      <span>We are identified as a critical entity under directive (EU) 2022/2557 (CER).</span>
    </label>

    <div className="scope-actions">
      <button className="primary-button" type="submit" disabled={status === "saving" || !sectorKey} aria-busy={status === "saving"}>
        {status === "saving" ? "Saving…" : declared ? "Update the declaration" : "Determine our position"}
      </button>
      {declared?.updatedAt ? <span className="muted">Last declared {new Date(declared.updatedAt).toLocaleDateString()}</span> : null}
    </div>
    {error ? <p className="error-text" role="alert">{error}</p> : null}
  </form>;
}
