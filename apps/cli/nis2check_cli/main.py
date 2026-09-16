"""CLI entry point. It has no dependency on hosted services or databases."""

import asyncio
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from nis2check_catalog import load_catalog, required_scopes
from nis2check_collector.auth import MsalAuthenticator
from nis2check_collector.engine import CollectorEngine
from nis2check_collector.graph import AsyncGraphClient
from nis2check_collector.models import RunResult, Verdict
from nis2check_reporting import (
    PdfUnavailableError,
    follow_up,
    render_dossier_html,
    render_html,
    verdict_tally,
    write_pdf,
)
from nis2check_scoping import (
    NOT_LISTED,
    Classification,
    OrganisationProfile,
    classify,
    find_sector,
    sectors_by_annex,
)

app = typer.Typer(no_args_is_help=True, help="Read-only NIS2 evidence collection for Microsoft 365.")
ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = ROOT / "packages" / "catalog" / "controls"
CLASSIFICATION_COLOUR: dict[Classification, str] = {
    Classification.ESSENTIAL: typer.colors.RED,
    Classification.IMPORTANT: typer.colors.YELLOW,
    Classification.OUT_OF_SCOPE: typer.colors.GREEN,
    Classification.UNDETERMINED: typer.colors.CYAN,
}
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


def load_profile(path: Path | None) -> OrganisationProfile | None:
    """Read a scoping profile written by `nis2check scope`, if one was given."""
    if path is None:
        return None
    return OrganisationProfile.model_validate_json(path.read_text(encoding="utf-8"))


def write_dossier(
    result: RunResult, output: Path, profile: OrganisationProfile | None
) -> None:
    """Render and write the PDF dossier, explaining plainly when the renderer is missing."""
    scoping = classify(profile) if profile is not None else None
    html = render_dossier_html(result, scoping=scoping, profile=profile)
    try:
        write_pdf(html, output)
    except PdfUnavailableError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"Dossier written to {output}")


@app.command()
def sectors() -> None:
    """List the annex I and annex II activities `nis2check scope --sector` accepts."""
    for annex, entries in sorted(sectors_by_annex().items()):
        typer.secho(f"\nAnnex {annex}", bold=True)
        for sector in entries:
            typer.echo(f"  {sector.key}\t{sector.sector} — {sector.subsector}")
    typer.echo(f"\n  {NOT_LISTED}\tNone of these activities")


@app.command()
def scope(
    sector: Annotated[str, typer.Option(help="Activity key from `nis2check sectors`")],
    employees: Annotated[int | None, typer.Option(help="Headcount")] = None,
    turnover: Annotated[float | None, typer.Option(help="Annual turnover in euro")] = None,
    balance: Annotated[float | None, typer.Option(help="Balance sheet total in euro")] = None,
    name: Annotated[str | None, typer.Option(help="Organisation name, for the dossier cover")] = None,
    registration_number: Annotated[str | None, typer.Option(help="Company registration number")] = None,
    sole_provider: Annotated[bool, typer.Option(help="Sole provider of an essential service (article 2(2)(b))")] = False,
    critical_entity: Annotated[bool, typer.Option(help="Identified as critical under directive (EU) 2022/2557")] = False,
    output: Annotated[Path | None, typer.Option(help="Write the profile here for `run --profile`")] = None,
) -> None:
    """Classify the organisation as essential, important or out of scope.

    Self-declared, not collected. It decides whether the directive applies; the controls
    decide what the tenant can show.
    """
    if sector != NOT_LISTED and find_sector(sector) is None:
        raise typer.BadParameter(f"Unknown activity '{sector}'. Run `nis2check sectors` for the list.")
    profile = OrganisationProfile(
        sector_key=sector,
        employees=employees,
        annual_turnover_eur=None if turnover is None else Decimal(str(turnover)),
        balance_sheet_total_eur=None if balance is None else Decimal(str(balance)),
        sole_provider=sole_provider,
        critical_entity_cer=critical_entity,
        name=name,
        registration_number=registration_number,
    )
    outcome = classify(profile)
    typer.echo("")
    typer.secho(
        f"  {outcome.classification.replace('_', ' ')}",
        bold=True,
        fg=CLASSIFICATION_COLOUR[outcome.classification],
    )
    typer.echo("")
    typer.echo(f"  {outcome.rationale}")
    typer.echo("")
    for line in outcome.supervision:
        typer.echo(f"    - {line}")
    typer.echo("")
    typer.secho(f"  Basis: {', '.join(outcome.legal_basis)}", fg=typer.colors.BRIGHT_BLACK)
    if output is not None:
        output.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        typer.echo("")
        typer.echo(f"  Profile written to {output}")
    typer.echo("")
    typer.secho(
        "  Based on what you declared, not on anything read from a tenant.",
        fg=typer.colors.BRIGHT_BLACK,
    )
    typer.echo("")


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
    pdf: Annotated[Path | None, typer.Option(help="Also render the PDF evidence dossier to this path")] = None,
    profile: Annotated[Path | None, typer.Option(help="Scoping profile from `nis2check scope`, for the dossier cover")] = None,
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
        html.write_text(render_html(result), encoding="utf-8")
        typer.echo(f"Report written to {html}")
    if pdf is not None:
        write_dossier(result, pdf, load_profile(profile))
    echo_summary(result)
    if html is None and pdf is None:
        typer.echo("")
        typer.echo(f"  Share the evidence: nis2check report {output}")


@app.command()
def report(
    source: Annotated[Path, typer.Argument(help="JSON result produced by `nis2check run`")],
    output: Annotated[Path, typer.Option(help="HTML report output path")] = Path("nis2check-report.html"),
    pdf: Annotated[Path | None, typer.Option(help="Also render the PDF evidence dossier to this path")] = None,
    profile: Annotated[Path | None, typer.Option(help="Scoping profile from `nis2check scope`, for the dossier cover")] = None,
) -> None:
    """Render a self-contained HTML evidence report from a JSON run result."""
    result = RunResult.model_validate_json(source.read_text(encoding="utf-8"))
    output.write_text(render_html(result), encoding="utf-8")
    typer.echo(f"Report written to {output}")
    if pdf is not None:
        write_dossier(result, pdf, load_profile(profile))
    echo_summary(result)
