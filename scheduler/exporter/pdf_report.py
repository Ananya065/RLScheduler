"""
PDF report generator. Builds a multi-page, professional research-style PDF
combining the metrics table with the real charts from
scheduler.visualization.charts — no chart or number here is placeholder
data; every figure embedded is generated fresh from the actual SimResult
data passed in.
"""

from pathlib import Path
from typing import Dict
import tempfile

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from scheduler.algorithms.base import SimResult
from scheduler.visualization.charts import generate_all_charts
from scheduler.utils.logging_config import get_logger

logger = get_logger(__name__)


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontSize=22, leading=26, spaceAfter=6,
                               textColor=colors.HexColor("#0d1119"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="ReportSubtitle", fontSize=11, textColor=colors.HexColor("#555555"),
                               spaceAfter=18))
    styles.add(ParagraphStyle(name="SectionHeading", fontSize=15, spaceBefore=18, spaceAfter=8,
                               textColor=colors.HexColor("#0d1119"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Caption", fontSize=9, textColor=colors.HexColor("#666666"),
                               spaceAfter=14, spaceBefore=2))
    styles.add(ParagraphStyle(name="Note", fontSize=9, textColor=colors.HexColor("#888888"),
                               spaceAfter=10, leading=13))
    return styles


def _metrics_table(metrics: Dict[str, Dict]):
    cols = ["Algorithm", "Avg Wait", "Avg TAT", "Avg Resp", "CPU%", "Switches", "Fairness", "Efficiency"]
    rows = [cols]
    for name, m in metrics.items():
        rows.append([
            name,
            f"{m['avg_waiting_time']:.1f}",
            f"{m['avg_turnaround_time']:.1f}",
            f"{m['avg_response_time']:.1f}",
            f"{m['cpu_utilization']*100:.1f}",
            str(m["context_switches"]),
            f"{m['fairness_index']:.3f}",
            f"{m['scheduling_efficiency_score']:.1f}",
        ])

    table = Table(rows, hAlign="LEFT", colWidths=[95, 55, 55, 55, 45, 55, 55, 60])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1119")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f7")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def generate_pdf_report(
    results: Dict[str, SimResult],
    metrics: Dict[str, Dict],
    workload_meta: Dict,
    output_path: Path,
    chart_dir: Path = None,
) -> Path:
    """Generate the full PDF report. Charts are (re)generated into chart_dir
    (a temp directory if not given) before being embedded, so the report
    always reflects the exact `results`/`metrics` passed in — never stale
    images left over from a previous run."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _build_styles()

    with tempfile.TemporaryDirectory() as tmp:
        chart_dir = chart_dir or Path(tmp)
        charts = generate_all_charts(results, metrics, chart_dir)

        doc = SimpleDocTemplate(
            str(output_path), pagesize=letter,
            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        )
        story = []

        # ---- Cover / summary page ----
        story.append(Paragraph("CPU Scheduling Simulation Report", styles["ReportTitle"]))
        story.append(Paragraph(
            f"Workload: {workload_meta.get('n_processes', 'n/a')} processes &middot; "
            f"seed {workload_meta.get('seed', 'n/a')} &middot; "
            f"Round Robin quantum {workload_meta.get('quantum', 'n/a')}",
            styles["ReportSubtitle"]
        ))
        story.append(Paragraph("Algorithm Comparison Table", styles["SectionHeading"]))
        story.append(_metrics_table(metrics))
        story.append(Paragraph(
            "Fairness = Jain's Fairness Index (standard). Efficiency = a designed composite "
            "heuristic (100 &times; CPU utilization &times; fairness / (1 + starvation)), "
            "original to this project — not a standard OS metric. See README for full definitions.",
            styles["Note"]
        ))

        story.append(Paragraph("Comparison Charts", styles["SectionHeading"]))
        for key, caption in [
            ("bar_waiting_time", "Average Waiting Time by Algorithm"),
            ("bar_turnaround_time", "Average Turnaround Time by Algorithm"),
            ("bar_response_time", "Average Response Time by Algorithm"),
            ("bar_context_switches", "Context Switches by Algorithm"),
            ("bar_throughput", "Throughput by Algorithm"),
        ]:
            story.append(RLImage(str(charts[key]), width=6.2 * inch, height=6.2 * inch * 4.5 / 7))
            story.append(Paragraph(caption, styles["Caption"]))

        story.append(RLImage(str(charts["radar"]), width=5 * inch, height=5 * inch))
        story.append(Paragraph("Multi-metric radar comparison (normalized per metric).", styles["Caption"]))

        story.append(RLImage(str(charts["heatmap"]), width=6.2 * inch, height=6.2 * inch * 3.5 / 9))
        story.append(Paragraph("Performance heatmap — green indicates the better value per column.", styles["Caption"]))

        story.append(RLImage(str(charts["pie_context_switch_share"]), width=4 * inch, height=4 * inch))
        story.append(Paragraph("Share of total context switches contributed by each algorithm.", styles["Caption"]))

        story.append(RLImage(str(charts["gauge_avg_cpu_utilization"]), width=4.5 * inch, height=2.7 * inch))
        story.append(Paragraph("Average CPU utilization across all algorithms in this run.", styles["Caption"]))

        # ---- Per-algorithm detail pages ----
        for name, result in results.items():
            story.append(PageBreak())
            story.append(Paragraph(f"Detail — {name}", styles["SectionHeading"]))
            safe_name = name.replace(" ", "_").replace("(", "").replace(")", "").replace("=", "")

            story.append(RLImage(str(charts[f"gantt_{safe_name}"]), width=6.2 * inch,
                                  height=min(6.2 * inch * 0.4, 4 * inch)))
            story.append(Paragraph(f"Execution timeline (Gantt) — {name}", styles["Caption"]))

            story.append(RLImage(str(charts[f"pie_busy_idle_{safe_name}"]), width=3.2 * inch, height=3.2 * inch))
            story.append(Paragraph(f"Busy vs. idle CPU time — {name}", styles["Caption"]))

            m = metrics[name]
            detail_rows = [
                ["Metric", "Value"],
                ["Avg Waiting Time", f"{m['avg_waiting_time']:.2f} ticks"],
                ["Avg Turnaround Time", f"{m['avg_turnaround_time']:.2f} ticks"],
                ["Avg Response Time", f"{m['avg_response_time']:.2f} ticks"],
                ["CPU Utilization", f"{m['cpu_utilization']*100:.1f}%"],
                ["Idle CPU Time", f"{m['idle_cpu_time']} ticks ({m['idle_cpu_percentage']*100:.1f}%)"],
                ["Throughput", f"{m['throughput']:.4f} proc/tick"],
                ["Context Switches", str(m["context_switches"])],
                ["Fairness Index", f"{m['fairness_index']:.3f}"],
                ["Starvation Score", f"{m['starvation_score']:.2f}"],
                ["Scheduling Efficiency Score", f"{m['scheduling_efficiency_score']:.1f} / 100"],
                ["Energy Score (simulated)", f"{m['energy_score']:.0f} units"],
                ["Cache Miss Rate (simulated)", f"{m['cache_miss_rate']*100:.1f}%"],
            ]
            t = Table(detail_rows, colWidths=[220, 200], hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d1119")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f7")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)

        doc.build(story)

    logger.info(f"Generated PDF report -> {output_path}")
    return output_path
