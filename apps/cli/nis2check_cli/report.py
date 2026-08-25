"""Self-contained evidence report rendering."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from nis2check_collector.models import RunResult


def render_html(result: RunResult, template_directory: Path) -> str:
    """Render an auditor-portable HTML report with no third-party resources."""
    environment = Environment(
        loader=FileSystemLoader(template_directory),
        autoescape=select_autoescape(["html"]),
    )
    template = environment.get_template("report.html.j2")
    return template.render(run=result, findings=result.findings)
