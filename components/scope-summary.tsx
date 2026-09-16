import { Classification, ScopingResult } from "@/lib/types";

const LABEL: Record<Classification, string> = {
  ESSENTIAL: "Essential entity",
  IMPORTANT: "Important entity",
  OUT_OF_SCOPE: "Not in scope",
  UNDETERMINED: "Not yet determined",
};

const MEANING: Record<Classification, string> = {
  ESSENTIAL: "The directive applies, with proactive supervision.",
  IMPORTANT: "The directive applies, with supervision after the fact.",
  OUT_OF_SCOPE: "The directive does not apply to this entity of its own accord.",
  UNDETERMINED: "Scope could not be settled on the figures that were declared.",
};

const SIZE_LABEL: Record<string, string> = {
  MICRO: "micro enterprise",
  SMALL: "small enterprise",
  MEDIUM: "medium-sized enterprise",
  LARGE: "large enterprise",
  UNDETERMINED: "size not determined",
};

/** The classification with the reasoning and the articles it rests on — never a score. */
export function ScopeSummary({ scoping }: { scoping: ScopingResult }) {
  return <section className="card scope-summary">
    <div className="scope-head">
      <span className={`scope-badge scope-${scoping.classification.toLowerCase()}`}>{LABEL[scoping.classification]}</span>
      <span className="muted">{SIZE_LABEL[scoping.size] || scoping.size}</span>
    </div>
    <p className="scope-meaning">{MEANING[scoping.classification]}</p>
    <p>{scoping.rationale}</p>
    {scoping.sector ? <p className="muted">{scoping.sector.sector} — {scoping.sector.subsector} (annex {scoping.sector.annexPoint})</p> : null}
    {scoping.supervision.length > 0 ? <>
      <h3>What this means</h3>
      <ul className="scope-obligations">{scoping.supervision.map((line) => <li key={line}>{line}</li>)}</ul>
    </> : null}
    <p className="muted scope-basis">Basis: {scoping.legalBasis.join(" · ")}</p>
    <p className="muted">Based on what you declared, not on anything read from your tenant. A Member State may designate an entity regardless of these rules.</p>
  </section>;
}
