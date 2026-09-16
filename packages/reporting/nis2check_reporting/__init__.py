"""Rendering findings into something a person reads: the HTML report and the PDF dossier.

Pure presentation. It takes findings and a scoping result and returns a document. It knows
nothing about Graph, databases or HTTP, which is why the CLI and the hosted API can both use
it without either depending on the other.
"""

from pathlib import Path

from .dossier import (
    CLASSIFICATION_HINT,
    PdfUnavailableError,
    endpoint_index,
    measure_coverage,
    open_limits,
    render_dossier_html,
    write_pdf,
)
from .report import (
    FOLLOW_UP,
    VERDICT_HINT,
    VERDICT_ORDER,
    domain_label,
    follow_up,
    group_by_domain,
    render_html,
    verdict_tally,
)


def template_directory() -> Path:
    """The bundled Jinja templates, so a caller never has to know where they live."""
    return Path(__file__).parent / "templates"


__all__ = [
    "CLASSIFICATION_HINT",
    "FOLLOW_UP",
    "VERDICT_HINT",
    "VERDICT_ORDER",
    "PdfUnavailableError",
    "domain_label",
    "endpoint_index",
    "follow_up",
    "group_by_domain",
    "measure_coverage",
    "open_limits",
    "render_dossier_html",
    "render_html",
    "template_directory",
    "verdict_tally",
    "write_pdf",
]
