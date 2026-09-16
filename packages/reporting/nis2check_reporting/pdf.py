"""The evidence dossier as a PDF, drawn rather than converted.

ReportLab is pure Python, so this works on any runtime that can run the API, including
serverless ones where a renderer backed by C libraries could not be installed.

The layout is drawn here while the HTML dossier is a template, so the two can drift visually.
What they must not drift on is content, and that is why every section below is fed by the same
helpers the template uses: `measure_coverage`, `open_limits`, `endpoint_index`, `follow_up`,
`group_by_domain` and `verdict_tally`. A section added to one has to be added to the other, but
neither can quietly report something different from the other.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from nis2check_collector.models import Finding, RunResult, Verdict
from nis2check_scoping import OrganisationProfile, ScopingResult
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    ListItem,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .dossier import (
    CLASSIFICATION_HINT,
    endpoint_index,
    measure_coverage,
    open_limits,
)
from .report import FOLLOW_UP, VERDICT_HINT, domain_label, follow_up, group_by_domain, verdict_tally

# Contemporan, as far as a PDF can carry it.
BRAND = colors.HexColor("#0000f2")
BRAND_SOFT = colors.HexColor("#dde1ff")
BRAND_SOFTER = colors.HexColor("#f1f3ff")
LIME = colors.HexColor("#edff45")
INK = colors.HexColor("#0a0a23")
BODY = colors.HexColor("#33374a")
MUTED = colors.HexColor("#6a6e85")
LINE = colors.HexColor("#dde1f5")
TINT = colors.HexColor("#f6f7fd")

VERDICT_COLOUR: dict[Verdict, colors.Color] = {
    Verdict.FAIL: colors.HexColor("#c81e1e"),
    Verdict.PARTIAL: colors.HexColor("#b45309"),
    Verdict.PASS: colors.HexColor("#15803d"),
    Verdict.INCONCLUSIVE: MUTED,
    Verdict.NOT_APPLICABLE: MUTED,
}

#: Built-in Type 1 faces only: no font file has to exist on the runtime.
SANS = "Helvetica"
SANS_BOLD = "Helvetica-Bold"
SERIF_BOLD = "Times-Bold"
MONO = "Courier"

FOOTER_NOTE = "Nis2Check — technical evidence, not a conformance statement"
MARGIN = 16 * mm


def _style(name: str, **kwargs: Any) -> ParagraphStyle:
    base = {
        "fontName": SANS,
        "fontSize": 9,
        "leading": 13,
        "textColor": BODY,
        "alignment": TA_LEFT,
        "spaceAfter": 0,
    }
    return ParagraphStyle(name, **{**base, **kwargs})


STYLES = {
    "cover_brand": _style("cover_brand", fontSize=11, textColor=BRAND_SOFT, spaceAfter=8 * mm),
    "cover_title": _style("cover_title", fontName=SERIF_BOLD, fontSize=34, leading=36, textColor=colors.white, spaceAfter=6 * mm),
    "cover_lede": _style("cover_lede", fontSize=11, leading=16, textColor=BRAND_SOFT),
    "cover_label": _style("cover_label", fontSize=7.5, textColor=BRAND_SOFT),
    "cover_value": _style("cover_value", fontSize=9, textColor=colors.white),
    "cover_notice": _style("cover_notice", fontSize=8.5, leading=12, textColor=colors.HexColor("#07071c")),
    "cover_tally": _style("cover_tally", fontSize=8.5, textColor=BRAND_SOFT),
    "eyebrow": _style("eyebrow", fontSize=7.5, textColor=MUTED, spaceAfter=1.5 * mm),
    "h2": _style("h2", fontName=SERIF_BOLD, fontSize=18, leading=21, textColor=INK, spaceAfter=2 * mm),
    "h3": _style("h3", fontName=SANS_BOLD, fontSize=10, leading=13, textColor=INK, spaceAfter=2 * mm),
    "h4": _style("h4", fontName=SANS_BOLD, fontSize=9.5, leading=12.5, textColor=INK),
    "lead": _style("lead", fontSize=10, leading=14.5, textColor=INK, spaceAfter=4 * mm),
    "body": _style("body", spaceAfter=2.5 * mm),
    "muted": _style("muted", fontSize=8.5, leading=12, textColor=MUTED),
    "cell": _style("cell", fontSize=8.5, leading=11.5),
    "cell_muted": _style("cell_muted", fontSize=7.5, leading=10, textColor=MUTED),
    "th": _style("th", fontName=SANS_BOLD, fontSize=7.5, leading=10, textColor=MUTED),
    "field_label": _style("field_label", fontName=SANS_BOLD, fontSize=7, leading=9, textColor=MUTED, spaceAfter=1 * mm),
    "step": _style("step", fontSize=8.5, leading=11.5),
    "endpoint": _style("endpoint", fontName=MONO, fontSize=7.5, leading=10, textColor=BODY),
}


def _escape(value: object) -> str:
    """Paragraph text is mini-HTML, so anything from a tenant has to be neutralised."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _verdict_label(verdict: Verdict) -> str:
    return verdict.replace("_", " ")


def _hex(colour: colors.Color) -> str:
    """ReportLab's inline markup wants `#rrggbb`; hexval() gives `0xrrggbb`."""
    return "#" + str(colour.hexval())[2:]


def _coloured(text: str, colour: colors.Color, bold: bool = True) -> str:
    inner = f"<b>{_escape(text)}</b>" if bold else _escape(text)
    return f'<font color="{_hex(colour)}">{inner}</font>'


def _draw_cover(canvas: Canvas, doc: BaseDocTemplate) -> None:
    canvas.saveState()
    canvas.setFillColor(BRAND)
    canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    canvas.restoreState()


def _draw_footer(canvas: Canvas, doc: BaseDocTemplate) -> None:
    canvas.saveState()
    canvas.setFont(SANS, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 12 * mm, FOOTER_NOTE)
    canvas.drawRightString(A4[0] - MARGIN, 12 * mm, f"{doc.page - 1}")
    canvas.restoreState()


#: A `None` width is ReportLab's "size this column to its content".
ColumnWidths = list[float | None]


def _table(rows: list[list[Any]], widths: ColumnWidths, header: bool = True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands: list[tuple[Any, ...]] = [
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), TINT))
    table.setStyle(TableStyle(commands))
    return table


def _section(number: str, title: str) -> list[Any]:
    return [
        Paragraph(_escape(number.upper()), STYLES["eyebrow"]),
        Paragraph(_escape(title), STYLES["h2"]),
        _rule(),
        Spacer(1, 4 * mm),
    ]


def _rule() -> Table:
    rule = Table([[""]], colWidths=[A4[0] - 2 * MARGIN], rowHeights=[1.6])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return rule


def _cover_story(
    result: RunResult,
    generated_at: datetime,
    scoping: ScopingResult | None,
    profile: OrganisationProfile | None,
) -> list[Any]:
    facts: list[tuple[str, str]] = []
    if profile and profile.name:
        facts.append(("ORGANISATION", profile.name))
    if profile and profile.registration_number:
        facts.append(("REGISTRATION", profile.registration_number))
    facts.extend(
        [
            ("TENANT", result.tenant_id),
            ("COLLECTED", result.started_at.strftime("%Y-%m-%d %H:%M UTC")),
            ("GENERATED", generated_at.strftime("%Y-%m-%d %H:%M UTC")),
            ("TOOL VERSION", result.tool_version),
            ("CONTROLS RUN", str(len(result.findings))),
        ]
    )
    fact_rows = [
        [Paragraph(label, STYLES["cover_label"]), Paragraph(_escape(value), STYLES["cover_value"])]
        for label, value in facts
    ]
    fact_table = Table(fact_rows, colWidths=[38 * mm, None], hAlign="LEFT")
    fact_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1.6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
            ]
        )
    )

    notice = Table(
        [[Paragraph(
            "This dossier reports evidence, not compliance. NIS2 is largely organisational; what "
            "can be read from a tenant is only part of article 21(2), and no part of this document "
            "is a conformance statement.",
            STYLES["cover_notice"],
        )]],
        colWidths=[130 * mm],
        hAlign="LEFT",
    )
    notice.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIME), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))

    tally = " · ".join(
        f"{count} {_verdict_label(verdict).lower()}" for verdict, count in verdict_tally(result.findings)
    )

    story: list[Any] = [
        Paragraph("Nis2Check", STYLES["cover_brand"]),
        Paragraph("Evidence dossier", STYLES["cover_title"]),
        Paragraph(
            "Technically verifiable evidence for NIS2 article 21(2), read from Microsoft 365 "
            "with read-only Microsoft Graph queries.",
            STYLES["cover_lede"],
        ),
        Spacer(1, 18 * mm),
    ]
    if scoping:
        story.append(_classification_badge(scoping.classification, on_brand=True))
        story.append(Spacer(1, 6 * mm))
    story.extend([fact_table, Spacer(1, 18 * mm), notice, Spacer(1, 6 * mm), Paragraph(_escape(tally), STYLES["cover_tally"])])
    return story


def _classification_badge(classification: str, on_brand: bool = False) -> Table:
    """A classification is a fact about the organisation, so it never uses the verdict palette."""
    background = colors.white if on_brand else BRAND_SOFTER
    text_colour = BRAND
    label = classification.replace("_", " ")
    width = stringWidth(label, SANS_BOLD, 11) + 16
    badge = Table(
        [[Paragraph(f'<font color="{_hex(text_colour)}"><b>{_escape(label)}</b></font>', _style("badge", fontSize=11))]],
        colWidths=[width],
        hAlign="LEFT",
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.5, BRAND if not on_brand else colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return badge


def _scope_story(scoping: ScopingResult, number: str) -> list[Any]:
    story = _section(number, "Scope and classification")
    story.append(
        Paragraph(
            "Whether the directive applies, and as what. This rests on figures the organisation "
            "declared about itself. Nothing in this section was read from the tenant.",
            STYLES["lead"],
        )
    )
    story.append(_classification_badge(scoping.classification))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(_escape(CLASSIFICATION_HINT[scoping.classification]), STYLES["lead"]))
    story.append(Paragraph(_escape(scoping.rationale), STYLES["body"]))

    sector = (
        f"{scoping.sector.sector} — {scoping.sector.subsector}"
        if scoping.sector
        else "Not listed in annex I or annex II"
    )
    annex = f"Annex {scoping.sector.annex_point}" if scoping.sector else "—"
    in_scope = "Could not be settled" if scoping.in_scope is None else "Yes" if scoping.in_scope else "No"
    facts = [
        ("SECTOR", sector),
        ("ANNEX", annex),
        ("ENTERPRISE SIZE", scoping.size.replace("_", " ").lower()),
        ("IN SCOPE", in_scope),
        ("LEGAL BASIS", " · ".join(scoping.legal_basis)),
    ]
    rows = [[Paragraph(label, STYLES["th"]), Paragraph(_escape(value), STYLES["cell"])] for label, value in facts]
    facts_table = Table(rows, colWidths=[42 * mm, None], hAlign="LEFT")
    facts_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    story.extend([Spacer(1, 2 * mm), facts_table])

    if scoping.supervision:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("What this means", STYLES["h3"]))
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_escape(line), STYLES["cell"]), leftIndent=10) for line in scoping.supervision],
                bulletType="bullet",
                bulletColor=BRAND,
                bulletFontSize=8.5,
                leftIndent=12,
            )
        )
    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            "Directive (EU) 2022/2555, article 2 for scope and article 3 for the tier; enterprise "
            "size follows the annex to recommendation 2003/361/EC. A Member State may designate an "
            "entity regardless of these rules.",
            STYLES["muted"],
        )
    )
    return story


def _how_to_read_story(findings: Sequence[Finding], number: str) -> list[Any]:
    story = _section(number, "How to read this dossier")
    story.append(
        Paragraph(
            "Every finding carries the evidence it rests on and the limit of what that evidence proves.",
            STYLES["lead"],
        )
    )
    tally_cells = [
        [
            Paragraph(_coloured(str(count), VERDICT_COLOUR[verdict]), _style("count", fontSize=16, leading=19)),
            Paragraph(_escape(_verdict_label(verdict).upper()), STYLES["th"]),
        ]
        for verdict, count in verdict_tally(findings)
    ]
    tally_table = Table([[cell[0] for cell in tally_cells], [cell[1] for cell in tally_cells]], hAlign="LEFT")
    tally_table.setStyle(
        TableStyle([("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])
    )
    story.extend([tally_table, Spacer(1, 5 * mm)])

    rows: list[list[Any]] = [[Paragraph("VERDICT", STYLES["th"]), Paragraph("WHAT IT MEANS HERE", STYLES["th"])]]
    for verdict, hint in VERDICT_HINT.items():
        rows.append(
            [
                Paragraph(_coloured(_verdict_label(verdict), VERDICT_COLOUR[verdict]), STYLES["cell"]),
                Paragraph(_escape(hint), STYLES["cell"]),
            ]
        )
    story.append(_table(rows, [32 * mm, None]))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Deliberately absent", STYLES["h3"]))
    story.append(
        Paragraph(
            "There is no total and no percentage. A single number invites working towards the "
            "number rather than towards the measure, and it would hide which of the ten measures "
            "is unevidenced.",
            STYLES["body"],
        )
    )
    story.append(
        Paragraph(
            "Nothing was guessed. Where evidence could not be read, the verdict is "
            f"{_coloured('INCONCLUSIVE', MUTED)} and the reason is stated with it.",
            STYLES["body"],
        )
    )
    return story


def _coverage_story(findings: Sequence[Finding], number: str) -> list[Any]:
    story = _section(number, "Coverage of article 21(2)")
    story.append(
        Paragraph(
            "The ten risk-management measures, and what this run could say about each. A measure "
            "with no finding is not a measure that is met.",
            STYLES["lead"],
        )
    )
    rows: list[list[Any]] = [
        [
            Paragraph("", STYLES["th"]),
            Paragraph("MEASURE", STYLES["th"]),
            Paragraph("CONTROLS", STYLES["th"]),
            Paragraph("VERDICTS", STYLES["th"]),
        ]
    ]
    for letter, title, measure_findings, measure_tally in measure_coverage(findings):
        ids = ", ".join(item.control_id for item in measure_findings)
        measure = Paragraph(
            _escape(title) + (f'<br/><font size="7.5" color="#6a6e85">{_escape(ids)}</font>' if ids else ""),
            STYLES["cell"],
        )
        verdicts = (
            " ".join(
                _coloured(f"{count} {_verdict_label(verdict).lower()}", VERDICT_COLOUR[verdict])
                for verdict, count in measure_tally
                if count
            )
            or '<font color="#6a6e85"><i>no control</i></font>'
        )
        rows.append(
            [
                Paragraph(f"<b>({_escape(letter)})</b>", STYLES["cell"]),
                measure,
                Paragraph(str(len(measure_findings)), STYLES["cell"]),
                Paragraph(verdicts, STYLES["cell"]),
            ]
        )
    story.append(_table(rows, [9 * mm, None, 20 * mm, 40 * mm]))
    return story


def _follow_up_story(findings: Sequence[Finding], number: str) -> list[Any]:
    pending = follow_up(findings)
    story = _section(number, "Findings that need follow-up")
    if not pending:
        story.append(
            Paragraph(
                "No control needs follow-up: every check is evidenced or does not apply to this "
                "tenant. The limits in appendix A still bound what that means.",
                STYLES["lead"],
            )
        )
        return story
    story.append(
        Paragraph(
            f"{len(pending)} of {len(findings)} controls failed, were only partly evidenced, or "
            "could not be read. Each one is set out in full in the next section.",
            STYLES["lead"],
        )
    )
    rows: list[list[Any]] = [
        [Paragraph("CONTROL", STYLES["th"]), Paragraph("VERDICT", STYLES["th"]), Paragraph("FINDING", STYLES["th"])]
    ]
    for finding in pending:
        rows.append(
            [
                Paragraph(f"<b>{_escape(finding.control_id)}</b>", STYLES["cell"]),
                Paragraph(_coloured(_verdict_label(finding.verdict), VERDICT_COLOUR[finding.verdict]), STYLES["cell"]),
                Paragraph(
                    f"{_escape(finding.title)}<br/>"
                    f'<font size="7.5" color="#6a6e85">{_escape(finding.nis2)} · '
                    f"{_escape(domain_label(finding.domain))}</font>",
                    STYLES["cell"],
                ),
            ]
        )
    story.append(_table(rows, [16 * mm, 30 * mm, None]))
    return story


def _finding_block(finding: Finding) -> KeepTogether:
    """One finding, kept on a single page so an auditor never reads half of it."""
    colour = VERDICT_COLOUR[finding.verdict]
    head = Table(
        [
            [
                Paragraph(
                    f'<font color="#6a6e85">{_escape(finding.control_id)}</font> '
                    f"<b>{_escape(finding.title)}</b>",
                    STYLES["h4"],
                ),
                Paragraph(_coloured(_verdict_label(finding.verdict), colour), _style("badge", fontSize=7.5, alignment=2)),
            ]
        ],
        colWidths=[None, 30 * mm],
        hAlign="LEFT",
    )
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))

    inner: list[Any] = [
        head,
        Spacer(1, 1.5 * mm),
        Paragraph(f"NIS2 {_escape(finding.nis2)}", STYLES["muted"]),
        Spacer(1, 2 * mm),
        Paragraph(_escape(finding.rationale), _style("rationale", textColor=INK)),
    ]
    if finding.verdict in FOLLOW_UP and finding.remediation_steps:
        inner.extend(
            [
                Spacer(1, 2.5 * mm),
                Paragraph("HOW TO REMEDIATE", STYLES["field_label"]),
                ListFlowable(
                    [ListItem(Paragraph(_escape(step), STYLES["step"]), leftIndent=12) for step in finding.remediation_steps],
                    bulletType="1",
                    bulletColor=BRAND,
                    bulletFontName=SANS_BOLD,
                    bulletFontSize=8.5,
                    leftIndent=14,
                ),
                Spacer(1, 1.5 * mm),
                Paragraph(f'<font color="#0000f2">{_escape(finding.remediation)}</font>', STYLES["muted"]),
            ]
        )
    if finding.limits.strip():
        inner.extend(
            [
                Spacer(1, 2.5 * mm),
                Paragraph("WHAT THIS DOES NOT PROVE", STYLES["field_label"]),
                Paragraph(_escape(finding.limits.strip()), STYLES["cell"]),
            ]
        )
    inner.extend(
        [
            Spacer(1, 2.5 * mm),
            Paragraph("READ FROM", STYLES["field_label"]),
            Paragraph("<br/>".join(_escape(endpoint) for endpoint in finding.endpoints), STYLES["endpoint"]),
        ]
    )

    card = Table([[inner]], colWidths=[A4[0] - 2 * MARGIN], hAlign="LEFT")
    card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LINEBEFORE", (0, 0), (0, -1), 2.2, colour),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return KeepTogether([card, Spacer(1, 3 * mm)])


def _findings_story(findings: Sequence[Finding], number: str) -> list[Any]:
    story = _section(number, "Findings in full")
    story.append(
        Paragraph(
            "Grouped by domain, follow-up first within each. The rationale is our reading; the raw "
            "Graph response it rests on is in the JSON result that accompanies this dossier.",
            STYLES["lead"],
        )
    )
    for domain, domain_findings in group_by_domain(findings):
        count = len(domain_findings)
        story.append(
            KeepTogether(
                [
                    Spacer(1, 3 * mm),
                    Paragraph(
                        f'{_escape(domain_label(domain))} <font size="8" color="#6a6e85">'
                        f'{count} control{"" if count == 1 else "s"}</font>',
                        _style("domain", fontName=SANS_BOLD, fontSize=11, leading=14, textColor=INK),
                    ),
                    Spacer(1, 2.5 * mm),
                ]
            )
        )
        story.extend(_finding_block(finding) for finding in domain_findings)
    return story


def _limits_story(findings: Sequence[Finding]) -> list[Any]:
    story = _section("Appendix A", "What this dossier does not prove")
    story.append(
        Paragraph(
            "Every control's stated limit, including the passing ones. A passing control whose "
            "limit is not read is the easiest way for a dossier to mislead.",
            STYLES["lead"],
        )
    )
    rows: list[list[Any]] = [
        [Paragraph("CONTROL", STYLES["th"]), Paragraph("VERDICT", STYLES["th"]), Paragraph("LIMIT", STYLES["th"])]
    ]
    for finding in open_limits(findings):
        rows.append(
            [
                Paragraph(f"<b>{_escape(finding.control_id)}</b>", STYLES["cell"]),
                Paragraph(_coloured(_verdict_label(finding.verdict), VERDICT_COLOUR[finding.verdict]), STYLES["cell"]),
                Paragraph(_escape(finding.limits.strip()), STYLES["cell"]),
            ]
        )
    story.append(_table(rows, [16 * mm, 30 * mm, None]))
    return story


def _endpoints_story(result: RunResult, generated_at: datetime) -> list[Any]:
    story = _section("Appendix B", "Everything that was read")
    story.append(
        Paragraph(
            "Every Microsoft Graph endpoint this run queried, and the controls that queried it. "
            "All of them are GET requests; the collector holds no write permission and contains "
            "no write path.",
            STYLES["lead"],
        )
    )
    rows: list[list[Any]] = [[Paragraph("ENDPOINT", STYLES["th"]), Paragraph("CONTROLS", STYLES["th"])]]
    for endpoint, control_ids in endpoint_index(result.findings):
        rows.append(
            [
                Paragraph(_escape(endpoint), STYLES["endpoint"]),
                Paragraph(_escape(", ".join(control_ids)), STYLES["cell"]),
            ]
        )
    story.append(_table(rows, [None, 34 * mm]))
    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            f"Generated by Nis2Check {_escape(result.tool_version)} on "
            f"{generated_at.strftime('%Y-%m-%d')}. Technical evidence only; this document is not a "
            "NIS2 conformance statement.",
            STYLES["muted"],
        )
    )
    return story


def render_dossier_pdf(
    result: RunResult,
    *,
    scoping: ScopingResult | None = None,
    profile: OrganisationProfile | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    """The evidence dossier as PDF bytes. Needs no system libraries and no temporary files."""
    generated = generated_at or datetime.now(UTC)
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Nis2Check evidence dossier — {result.tenant_id}",
        author="Nis2Check",
        subject="Technical evidence for NIS2 article 21(2)",
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="cover",
                frames=[Frame(18 * mm, 24 * mm, A4[0] - 36 * mm, A4[1] - 48 * mm, id="cover")],
                onPage=_draw_cover,
            ),
            PageTemplate(
                id="body",
                frames=[Frame(MARGIN, 18 * mm, A4[0] - 2 * MARGIN, A4[1] - 36 * mm, id="body")],
                onPage=_draw_footer,
            ),
        ]
    )

    story: list[Any] = _cover_story(result, generated, scoping, profile)
    story.extend([NextPageTemplate("body"), PageBreak()])

    sections: list[list[Any]] = []
    if scoping:
        sections.append(_scope_story(scoping, "Section 1"))
    offset = 2 if scoping else 1
    sections.append(_how_to_read_story(result.findings, f"Section {offset}"))
    sections.append(_coverage_story(result.findings, f"Section {offset + 1}"))
    sections.append(_follow_up_story(result.findings, f"Section {offset + 2}"))
    sections.append(_findings_story(result.findings, f"Section {offset + 3}"))
    sections.append(_limits_story(result.findings))
    sections.append(_endpoints_story(result, generated))

    for index, section in enumerate(sections):
        story.extend(section)
        if index < len(sections) - 1:
            story.append(PageBreak())

    doc.build(story)
    return buffer.getvalue()
