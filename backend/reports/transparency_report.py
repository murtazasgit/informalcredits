"""
Transparency Report (PDF) — explains the credit decision in plain language.
Pure presentation: it renders the ScoreResult / ExplainResult / Recommendation objects that the
scoring, explainability and recommendation modules already produced. Nothing is recomputed here.
"""
import io
from datetime import datetime
from typing import Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from common.schemas import ExplainResult, Recommendation, ScoreResult

TIER_COLORS = {"Excellent": "#0d9f6e", "Good": "#2563eb", "Fair": "#d97706", "Poor": "#dc2626"}


def decision_summary(score: ScoreResult, recommendations: list[Recommendation]) -> tuple[str, str]:
    """(headline, detail) accept/reject wording derived from the existing recommendation list."""
    eligible = [r for r in recommendations if r.eligible]
    if eligible:
        best = eligible[0]
        return ("APPROVED FOR PRODUCTS",
                f"Score {score.total_score} qualifies for {len(eligible)} of {len(recommendations)} products. "
                f"Best match: {best.name} at {best.interest_rate:g}% interest.")
    nearest = min(recommendations, key=lambda r: r.min_score_required, default=None)
    if nearest is None:
        return "NO PRODUCTS AVAILABLE", "No products are currently in the catalogue."
    gap = nearest.min_score_required - score.total_score
    return ("NOT APPROVED",
            f"Score {score.total_score} is below every product minimum. The nearest product "
            f"({nearest.name}) requires {nearest.min_score_required}, i.e. {gap} more points.")


def build_transparency_report(
    score: ScoreResult,
    explanation: ExplainResult,
    recommendations: list[Recommendation],
    ml_score: Optional[dict] = None,
    generated_at: Optional[datetime] = None,
) -> bytes:
    styles = getSampleStyleSheet()
    h1, h2, body = styles["Title"], styles["Heading2"], styles["BodyText"]
    small = styles["BodyText"].clone("small", fontSize=8, textColor=colors.grey)
    generated_at = generated_at or datetime.now()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="AltCredit Transparency Report", author="AltCredit")
    story = [
        Paragraph("Credit Decision Transparency Report", h1),
        Paragraph(f"Applicant: {escape(score.user_id)} &nbsp;|&nbsp; Generated {generated_at:%Y-%m-%d %H:%M}", body),
        Spacer(1, 6),
    ]

    tier_color = TIER_COLORS.get(score.risk_category, "#555555")
    headline, detail = decision_summary(score, recommendations)
    story += [
        Paragraph(f'<font size="26" color="{tier_color}"><b>{score.total_score}</b></font> / 1000 &nbsp; '
                  f'<font color="{tier_color}"><b>{escape(score.risk_category)}</b></font>', body),
        Spacer(1, 4),
        Paragraph(f"<b>Decision: {headline}</b>", h2),
        Paragraph(escape(detail), body),
    ]

    story += [Paragraph("Why this score", h2), Paragraph(escape(explanation.summary_text), body), Spacer(1, 4)]
    rows = [["Factor", "Points", "Explanation"]]
    for f in explanation.factors:
        sign = "+" if f.points >= 0 else ""
        rows.append([Paragraph(escape(f.label), body), f"{sign}{f.points}", Paragraph(escape(f.text or ""), body)])
    table = Table(rows, colWidths=[55 * mm, 20 * mm, 95 * mm], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
             ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
             ("VALIGN", (0, 0), (-1, -1), "TOP")]
    for i, f in enumerate(explanation.factors, start=1):
        style.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#0d9f6e" if f.points >= 0 else "#dc2626")))
    table.setStyle(TableStyle(style))
    story.append(table)

    if ml_score:
        story += [Paragraph("Independent ML cross-check", h2),
                  Paragraph(f"A separately trained probability-of-default model estimates a score of "
                            f"<b>{ml_score.get('total_score')}</b> "
                            f"(default probability {ml_score.get('probability_of_default')}). "
                            f"The rule-based score above is the score of record.", body)]

    story.append(Paragraph("Product eligibility", h2))
    rec_rows = [["Product", "Rate", "Min score", "Result"]]
    for r in recommendations:
        rec_rows.append([Paragraph(escape(r.name), body), f"{r.interest_rate:g}%", str(r.min_score_required),
                         Paragraph(("Eligible: " if r.eligible else "Not yet: ") + escape(r.reason), body)])
    rtable = Table(rec_rows, colWidths=[45 * mm, 15 * mm, 20 * mm, 90 * mm], repeatRows=1)
    rtable.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                                ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(rtable)

    story += [Spacer(1, 10),
              Paragraph("This report is generated from alternative (non-bureau) data using a transparent, "
                        "rule-based point system. Every point above is traceable to an input you supplied. "
                        "It is an MVP demonstration and not a binding credit decision.", small)]
    doc.build(story)
    return buf.getvalue()
