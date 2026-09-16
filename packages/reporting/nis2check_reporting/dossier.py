"""The downloadable evidence dossier: one PDF an auditor can be handed.

The HTML report is for reading on screen and filtering. The dossier is the same evidence laid
out to be printed, paginated and archived, with the scope classification in front of it and the
queried endpoints behind it. Nothing here interprets more than the report does.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from nis2check_catalog import ARTICLE_21_2, measure_letter
from nis2check_collector.models import Finding, RunResult, Verdict
from nis2check_scoping import Classification, OrganisationProfile, ScopingResult

from .report import (
    FOLLOW_UP,
    VERDICT_HINT,
    VERDICT_ORDER,
    domain_label,
    follow_up,
    group_by_domain,
    verdict_tally,
)

TEMPLATE = "dossier.html.j2"

#: What a classification means for the reader of the dossier, in one line.
CLASSIFICATION_HINT: dict[Classification, str] = {
    Classification.ESSENTIAL: "The directive applies, with proactive supervision.",
    Classification.IMPORTANT: "The directive applies, with supervision after the fact.",
    Classification.OUT_OF_SCOPE: "The directive does not apply to this entity of its own accord.",
    Classification.UNDETERMINED: "Scope could not be settled on the figures that were declared.",
}


class PdfUnavailableError(RuntimeError):
    """WeasyPrint is installed but its system libraries are not."""


def measure_coverage(
    findings: Sequence[Finding],
) -> list[tuple[str, str, list[Finding], list[tuple[Verdict, int]]]]:
    """Every measure of article 21(2) with its findings and its own verdict tally.

    All ten measures stay in the list, including any the run produced no finding for. Dropping
    an empty measure would read as coverage that is not there.
    """
    buckets: dict[str, list[Finding]] = {letter: [] for letter in ARTICLE_21_2}
    for finding in findings:
        letter = measure_letter(finding.nis2)
        if letter is not None:
            buckets[letter].append(finding)
    return [
        (
            letter,
            title,
            sorted(buckets[letter], key=lambda item: item.control_id),
            verdict_tally(buckets[letter]),
        )
        for letter, title in ARTICLE_21_2.items()
    ]


def endpoint_index(findings: Sequence[Finding]) -> list[tuple[str, list[str]]]:
    """Every Graph endpoint the run read, with the controls that read it.

    This is the appendix that lets a reader check the claim that the tool only ever reads.
    """
    index: dict[str, list[str]] = {}
    for finding in findings:
        for endpoint in finding.endpoints:
            index.setdefault(endpoint, []).append(finding.control_id)
    return [(endpoint, sorted(set(controls))) for endpoint, controls in sorted(index.items())]


def open_limits(findings: Sequence[Finding]) -> list[Finding]:
    """Findings whose stated limits an auditor has to read, follow-up first.

    A PASS with a limit is exactly where a dossier misleads if the limit is not shown, so the
    passing controls are kept in.
    """
    return sorted(
        (finding for finding in findings if finding.limits.strip()),
        key=lambda item: (VERDICT_ORDER.index(item.verdict), item.control_id),
    )


def render_dossier_html(
    result: RunResult,
    template_directory: Path | None = None,
    *,
    scoping: ScopingResult | None = None,
    profile: OrganisationProfile | None = None,
) -> str:
    """Render the dossier as a self-contained, printable HTML document."""
    directory = template_directory or Path(__file__).parent / "templates"
    environment = Environment(loader=FileSystemLoader(directory), autoescape=True)
    environment.filters["domain_label"] = domain_label
    return environment.get_template(TEMPLATE).render(
        run=result,
        findings=result.findings,
        generated_at=datetime.now(UTC),
        scoping=scoping,
        profile=profile,
        classification_hint=CLASSIFICATION_HINT,
        measures=measure_coverage(result.findings),
        domains=group_by_domain(result.findings),
        tally=verdict_tally(result.findings),
        follow_up=follow_up(result.findings),
        limits=open_limits(result.findings),
        endpoints=endpoint_index(result.findings),
        hints=VERDICT_HINT,
        follow_up_verdicts=FOLLOW_UP,
    )


def write_pdf(html: str, output: Path, *, base_url: Path | None = None) -> None:
    """Write the dossier HTML to a PDF.

    WeasyPrint is imported here rather than at module import, so that `nis2check run` and the
    HTML report keep working on a machine where its Pango libraries are missing.
    """
    try:
        from weasyprint import HTML  # noqa: PLC0415 - optional at runtime by design
    except ImportError as error:  # pragma: no cover - depends on the install
        raise PdfUnavailableError(
            "PDF output needs WeasyPrint: pip install 'nis2check[pdf]'."
        ) from error
    except OSError as error:
        raise PdfUnavailableError(
            "WeasyPrint is installed but could not load its system libraries. "
            "On Debian or Ubuntu: apt-get install libpango-1.0-0 libpangoft2-1.0-0 "
            f"libharfbuzz0b libfontconfig1. The original error was: {error}"
        ) from error
    HTML(string=html, base_url=str(base_url or output.parent)).write_pdf(str(output))
