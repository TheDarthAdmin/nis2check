"""CLI entry point. It has no dependency on hosted services or databases."""

import asyncio
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from nis2check_catalog import load_catalog, required_scopes
from nis2check_collector.auth import MsalAuthenticator
from nis2check_collector.engine import CollectorEngine
from nis2check_collector.graph import AsyncGraphClient
from nis2check_collector.models import RunResult, Verdict

from .report import follow_up, render_html, verdict_tally

app = typer.Typer(no_args_is_help=True, help="Read-only NIS2 evidence collection for Microsoft 365.")
ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = ROOT / "packages" / "catalog" / "controls"
TEMPLATES = ROOT / "apps" / "cli" / "templates"
VERDICT_COLOUR: dict[Verdict, str] = {
    Verdict.FAIL: typer.colors.RED,
    Verdict.PARTIAL: typer.colors.YELLOW,
    Verdict.INCONCLUSIVE: typer.colors.CYAN,
    Verdict.PASS: typer.colors.GREEN,
    Verdict.NOT_APPLICABLE: typer.colors.BRIGHT_BLACK,
}


def echo_summary(result: RunResult) -> None:
    """Print what the run found, so the terminal is a usable first read of the evidence."""
    typer.echo("")
    typer.echo(
        "  "
        + "  ".join(
            typer.style(f"{count} {verdict.replace('_', ' ').lower()}", fg=VERDICT_COLOUR[verdict])
            for verdict, count in verdict_tally(result.findings)
        )
    )
    pending = follow_up(result.findings)
    if pending:
        typer.echo("")
        typer.secho("  Needs follow-up", bold=True)
        for finding in pending:
            verdict = typer.style(f"{finding.verdict:<14}", fg=VERDICT_COLOUR[finding.verdict])
            typer.echo(f"    {finding.control_id}  {verdict}{finding.title}")
        typer.echo("")
        typer.secho(
            "  The HTML report lists the remediation steps for each of these controls.",
            fg=typer.colors.BRIGHT_BLACK,
        )
    else:
        typer.echo("")
        typer.echo("  No control needs follow-up; every check is evidenced or not applicable.")
    typer.echo("")
    typer.secho(
        "  Technical evidence only. This is not a NIS2 conformance statement.",
        fg=typer.colors.BRIGHT_BLACK,
    )


@app.command()
def controls() -> None:
    """List bundled controls and their required Graph permissions."""
    for control in load_catalog(CATALOGUE):
        typer.echo(f"{control.id}\t{control.title}\t{', '.join(control.requires.scopes)}")


@app.command()
def run(
    tenant_id: Annotated[str, typer.Option(help="Microsoft Entra tenant ID")],
    client_id: Annotated[str, typer.Option(help="App registration client ID")],
    output: Annotated[Path, typer.Option(help="Path for the JSON run result")] = Path("nis2check.json"),
    html: Annotated[Path | None, typer.Option(help="Also render the HTML report to this path")] = None,
    certificate: Annotated[Path | None, typer.Option(help="PEM certificate private key")] = None,
    thumbprint: Annotated[str | None, typer.Option(help="Certificate thumbprint")] = None,
    device_code: Annotated[bool, typer.Option(help="Use interactive device-code authentication")] = False,
) -> None:
    """Run the bundled read-only controls and write a JSON evidence result."""
    if device_code == (certificate is not None or thumbprint is not None):
        raise typer.BadParameter("Choose --device-code or both --certificate and --thumbprint.")
    if certificate is None and not device_code:
        raise typer.BadParameter("Certificate authentication needs --certificate and --thumbprint.")
    auth = MsalAuthenticator(tenant_id, client_id, output.with_suffix(".msal-cache.json"))
    if device_code:
        token = auth.acquire_device_code_token(required_scopes(load_catalog(CATALOGUE)))
    else:
        assert certificate is not None and thumbprint is not None
        token = auth.acquire_certificate_token(certificate.read_text(encoding="utf-8"), thumbprint)

    async def collect() -> RunResult:
        async with AsyncGraphClient(token) as graph:
            return await CollectorEngine(graph, version("nis2check")).run(
                tenant_id,
                load_catalog(CATALOGUE),
            )

    result = asyncio.run(collect())
    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Evidence written to {output}")
    if html is not None:
        html.write_text(render_html(result, TEMPLATES), encoding="utf-8")
        typer.echo(f"Report written to {html}")
    echo_summary(result)
    if html is None:
        typer.echo("")
        typer.echo(f"  Share the evidence: nis2check report {output}")


@app.command()
def report(
    source: Annotated[Path, typer.Argument(help="JSON result produced by `nis2check run`")],
    output: Annotated[Path, typer.Option(help="HTML report output path")] = Path("nis2check-report.html"),
) -> None:
    """Render a self-contained HTML evidence report from a JSON run result."""
    result = RunResult.model_validate_json(source.read_text(encoding="utf-8"))
    output.write_text(render_html(result, TEMPLATES), encoding="utf-8")
    typer.echo(f"Report written to {output}")
    echo_summary(result)
