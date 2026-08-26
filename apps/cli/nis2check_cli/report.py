"""Self-contained evidence report rendering."""

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from nis2check_collector.models import Finding, RunResult, Verdict

#: Findings that need follow-up are shown first; a run is never reduced to a score.
VERDICT_ORDER: tuple[Verdict, ...] = (
    Verdict.FAIL,
    Verdict.PARTIAL,
    Verdict.INCONCLUSIVE,
    Verdict.PASS,
    Verdict.NOT_APPLICABLE,
)
FOLLOW_UP: frozenset[Verdict] = frozenset({Verdict.FAIL, Verdict.PARTIAL, Verdict.INCONCLUSIVE})
VERDICT_HINT: dict[Verdict, str] = {
    Verdict.FAIL: "The evidence contradicts the control.",
    Verdict.PARTIAL: "The control is only partly evidenced.",
    Verdict.INCONCLUSIVE: "The evidence could not be read; no assumption was made.",
    Verdict.PASS: "The evidence supports the control.",
    Verdict.NOT_APPLICABLE: "The control does not apply to this tenant.",
}


def domain_label(domain: str) -> str:
    """Turn a catalogue domain key into a human label."""
    return domain.replace("_", " ").capitalize()


def verdict_tally(findings: Sequence[Finding]) -> list[tuple[Verdict, int]]:
    """Count findings per verdict, in follow-up-first order. Deliberately no percentage."""
    counts = Counter(finding.verdict for finding in findings)
    return [(verdict, counts.get(verdict, 0)) for verdict in VERDICT_ORDER]


def follow_up(findings: Sequence[Finding]) -> list[Finding]:
    """Findings an auditor has to look at, in follow-up-first order."""
    return [finding for finding in _ordered(findings) if finding.verdict in FOLLOW_UP]


def group_by_domain(findings: Sequence[Finding]) -> list[tuple[str, list[Finding]]]:
    """Group findings by catalogue domain, follow-up-first within each domain."""
    domains: dict[str, list[Finding]] = {}
    for finding in _ordered(findings):
        domains.setdefault(finding.domain, []).append(finding)
    return sorted(domains.items())


def _ordered(findings: Sequence[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda item: (VERDICT_ORDER.index(item.verdict), item.control_id))


def render_html(result: RunResult, template_directory: Path) -> str:
    """Render an auditor-portable HTML report with no third-party resources."""
    # Autoescape unconditionally: the template is named `.html.j2`, which extension-based
    # selection does not recognise, and tenant strings reach the report through rationales.
    environment = Environment(loader=FileSystemLoader(template_directory), autoescape=True)
    environment.filters["domain_label"] = domain_label
    template = environment.get_template("report.html.j2")
    return template.render(
        run=result,
        findings=result.findings,
        domains=group_by_domain(result.findings),
        tally=verdict_tally(result.findings),
        follow_up=follow_up(result.findings),
        hints=VERDICT_HINT,
    )
