"""
Chart generation using matplotlib. Every function here takes REAL data
(a SimResult or a metrics dict computed by scheduler.metrics.calculator)
and renders it — nothing here draws placeholder or synthetic numbers.

These charts back the PDF report (scheduler/exporter/pdf_report.py) and are
also usable standalone for any PNG you want outside the browser dashboard.
The interactive browser dashboard (dashboard/scheduler_dashboard.html) has
its own, separate Chart.js-based rendering of the same underlying data —
duplication is intentional: one path works without a browser, one is
interactive.
"""

from pathlib import Path
from typing import Dict, List
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless — no display server required
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from scheduler.algorithms.base import SimResult

# ---- shared dark theme, matching the dashboard's palette ----
BG = "#07090d"
PANEL = "#0d1119"
GRID = "#232b3a"
TEXT = "#e9edf3"
TEXT_MUTED = "#7e8a9c"
CYAN = "#00d9ff"
VIOLET = "#b14eff"
AMBER = "#ffb020"
GREEN = "#3dffa0"
RED = "#ff4d6d"

PALETTE = [CYAN, VIOLET, GREEN, AMBER, RED, "#5eead4", "#f472b6", "#a3e635"]


def _style_axes(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.title.set_color(TEXT)
    ax.xaxis.label.set_color(TEXT_MUTED)
    ax.yaxis.label.set_color(TEXT_MUTED)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)


def _color_for_pid(pid: int) -> str:
    return PALETTE[pid % len(PALETTE)]


def plot_gantt_chart(result: SimResult, output_path: Path, title: str = None) -> Path:
    """Gantt chart of actual CPU execution segments (from Process.execution_history)."""
    fig, ax = plt.subplots(figsize=(11, max(2.5, 0.35 * max(len(result.processes), 1))))
    fig.patch.set_facecolor(BG)
    _style_axes(ax)

    if not result.processes:
        ax.text(0.5, 0.5, "No processes to display", color=TEXT_MUTED,
                ha="center", va="center", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
    else:
        procs_sorted = sorted(result.processes, key=lambda p: p.pid)
        for row, proc in enumerate(procs_sorted):
            for (start, end) in proc.execution_history:
                ax.barh(row, end - start, left=start, height=0.6,
                        color=_color_for_pid(proc.pid), edgecolor=BG, linewidth=0.5)
                if end - start > max(result.total_time * 0.015, 0.5):
                    ax.text((start + end) / 2, row, f"P{proc.pid}", ha="center", va="center",
                            fontsize=7, color="#0a0a0a", fontweight="bold")
        ax.set_yticks(range(len(procs_sorted)))
        ax.set_yticklabels([f"P{p.pid}" for p in procs_sorted])
        ax.set_xlim(0, max(result.total_time, 1))

    ax.set_xlabel("Time (ticks)")
    ax.set_title(title or f"Gantt Chart — {result.algorithm_name}", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BG, dpi=150)
    plt.close(fig)
    return output_path


def plot_metric_bar_comparison(metrics: Dict[str, Dict], metric_key: str, ylabel: str,
                                output_path: Path, title: str = None) -> Path:
    """Bar chart comparing one metric across all algorithms. Works for waiting
    time, turnaround time, response time, context switches, throughput, etc.
    — pass the metric_key you want."""
    names = list(metrics.keys())
    values = [metrics[n][metric_key] for n in names]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    fig.patch.set_facecolor(BG)
    _style_axes(ax)

    bars = ax.bar(names, values, color=[PALETTE[i % len(PALETTE)] for i in range(len(names))],
                   edgecolor=BG, linewidth=1)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{v:.2f}" if not float(v).is_integer() else f"{int(v)}",
                ha="center", va="bottom", color=TEXT, fontsize=9)

    ax.set_ylabel(ylabel)
    ax.set_title(title or ylabel, fontsize=12, fontweight="bold")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BG, dpi=150)
    plt.close(fig)
    return output_path


def plot_radar_comparison(metrics: Dict[str, Dict], output_path: Path) -> Path:
    """Radar chart across several normalized metrics, one line per algorithm."""
    radar_fields = [
        ("avg_waiting_time", "Wait"), ("avg_turnaround_time", "Turnaround"),
        ("context_switches", "Switches"), ("starvation_score", "Starvation"),
        ("energy_score", "Energy"), ("cache_miss_rate", "Cache Miss"),
    ]
    names = list(metrics.keys())
    labels = [f[1] for f in radar_fields]
    n_vars = len(labels)

    maxima = [max(metrics[n][f[0]] for n in names) or 1 for f in radar_fields]

    angles = np.linspace(0, 2 * np.pi, n_vars, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT_MUTED, labelsize=8)
    ax.spines["polar"].set_color(GRID)
    ax.grid(color=GRID)

    for i, name in enumerate(names):
        values = [metrics[name][f[0]] / maxima[j] for j, f in enumerate(radar_fields)]
        values += values[:1]
        ax.plot(angles, values, label=name, color=PALETTE[i % len(PALETTE)], linewidth=2)
        ax.fill(angles, values, color=PALETTE[i % len(PALETTE)], alpha=0.08)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color=TEXT_MUTED)
    ax.set_yticklabels([])
    ax.set_title("Multi-Metric Radar Comparison", color=TEXT, fontsize=12, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, facecolor=BG, dpi=150)
    plt.close(fig)
    return output_path


def plot_heatmap_comparison(metrics: Dict[str, Dict], output_path: Path) -> Path:
    """Heatmap of normalized metric values across algorithms."""
    fields = [
        ("avg_waiting_time", "Avg Wait", True), ("avg_turnaround_time", "Avg TAT", True),
        ("avg_response_time", "Avg Resp", True), ("fairness_index", "Fairness", False),
        ("starvation_score", "Starvation", True), ("context_switches", "Switches", True),
        ("cpu_utilization", "CPU Util", False), ("scheduling_efficiency_score", "Efficiency", False),
    ]
    names = list(metrics.keys())

    matrix = np.zeros((len(names), len(fields)))
    for i, name in enumerate(names):
        for j, (key, _, invert) in enumerate(fields):
            vals = [metrics[n][key] for n in names]
            lo, hi = min(vals), max(vals)
            norm = 0.5 if hi == lo else (metrics[name][key] - lo) / (hi - lo)
            matrix[i, j] = 1 - norm if invert else norm

    fig, ax = plt.subplots(figsize=(9, max(2, 0.6 * len(names) + 1)))
    fig.patch.set_facecolor(BG)
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(range(len(fields)))
    ax.set_xticklabels([f[1] for f in fields], color=TEXT_MUTED, fontsize=9, rotation=20, ha="right")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, color=TEXT_MUTED, fontsize=9)

    for i in range(len(names)):
        for j, (key, _, _) in enumerate(fields):
            raw = metrics[names[i]][key]
            text = f"{raw:.2f}" if not float(raw).is_integer() else f"{int(raw)}"
            ax.text(j, i, text, ha="center", va="center", fontsize=8, color="#0a0a0a", fontweight="bold")

    ax.set_title("Performance Heatmap (green = better)", color=TEXT, fontsize=12, fontweight="bold")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BG, dpi=150)
    plt.close(fig)
    return output_path


def plot_busy_idle_pie(result: SimResult, output_path: Path) -> Path:
    """Pie chart: fraction of total simulated time the CPU was busy vs idle."""
    total = max(result.total_time, 1)
    busy = total - result.idle_ticks
    idle = result.idle_ticks

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    fig.patch.set_facecolor(BG)
    wedges, texts, autotexts = ax.pie(
        [busy, idle], labels=["Busy", "Idle"], colors=[CYAN, GRID],
        autopct="%1.1f%%", startangle=90,
        textprops={"color": TEXT, "fontsize": 10},
        wedgeprops={"edgecolor": BG, "linewidth": 2},
    )
    ax.set_title(f"CPU Time Breakdown — {result.algorithm_name}", color=TEXT, fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BG, dpi=150)
    plt.close(fig)
    return output_path


def plot_context_switch_share_pie(metrics: Dict[str, Dict], output_path: Path) -> Path:
    """Pie chart: each algorithm's share of total context switches across
    the whole comparison — illustrates relative preemption overhead."""
    names = list(metrics.keys())
    values = [metrics[n]["context_switches"] for n in names]

    fig, ax = plt.subplots(figsize=(5, 5))
    fig.patch.set_facecolor(BG)
    if sum(values) == 0:
        ax.text(0.5, 0.5, "No context switches recorded", color=TEXT_MUTED, ha="center", va="center")
        ax.set_xticks([]); ax.set_yticks([])
    else:
        ax.pie(values, labels=names, colors=[PALETTE[i % len(PALETTE)] for i in range(len(names))],
               autopct="%1.1f%%", startangle=90,
               textprops={"color": TEXT, "fontsize": 9},
               wedgeprops={"edgecolor": BG, "linewidth": 2})
    ax.set_title("Context Switch Share by Algorithm", color=TEXT, fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, facecolor=BG, dpi=150)
    plt.close(fig)
    return output_path


def plot_cpu_utilization_gauge(cpu_utilization: float, output_path: Path, title: str = "CPU Utilization") -> Path:
    """Semi-circular gauge chart for a single utilization value (0-1)."""
    fig, ax = plt.subplots(figsize=(5, 3), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    theta_bg = np.linspace(np.pi, 0, 100)
    ax.bar(theta_bg, 1, width=(np.pi / 100), color=GRID, bottom=0, alpha=0.6)

    value = max(0.0, min(1.0, cpu_utilization))
    n_fill = max(int(value * 100), 1)
    theta_fill = np.linspace(np.pi, np.pi - np.pi * value, n_fill)
    color = GREEN if value > 0.7 else (AMBER if value > 0.4 else RED)
    ax.bar(theta_fill, 1, width=(np.pi / 100), color=color, bottom=0)

    ax.set_theta_zero_location("W")
    ax.set_theta_direction(1)
    ax.set_thetamin(0); ax.set_thetamax(180)
    ax.set_ylim(0, 1)
    ax.set_yticks([]); ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # axes-fraction placement (robust) rather than negative-radius polar
    # coordinates (which clip unpredictably against ylim).
    ax.annotate(f"{value*100:.1f}%", xy=(0.5, 0.15), xycoords="axes fraction",
                ha="center", va="center", fontsize=20, color=TEXT, fontweight="bold")
    ax.annotate(title, xy=(0.5, 0.0), xycoords="axes fraction",
                ha="center", va="center", fontsize=10, color=TEXT_MUTED)

    fig.tight_layout()
    fig.savefig(output_path, facecolor=BG, dpi=150)
    plt.close(fig)
    return output_path


def generate_all_charts(results: Dict[str, SimResult], metrics: Dict[str, Dict], output_dir: Path) -> Dict[str, Path]:
    """Generate the full standard chart set for a comparison run. Returns a
    dict of chart-name -> file path, used by the PDF report builder."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    for name, result in results.items():
        safe_name = name.replace(" ", "_").replace("(", "").replace(")", "").replace("=", "")
        paths[f"gantt_{safe_name}"] = plot_gantt_chart(result, output_dir / f"gantt_{safe_name}.png")
        paths[f"pie_busy_idle_{safe_name}"] = plot_busy_idle_pie(result, output_dir / f"pie_busy_idle_{safe_name}.png")

    paths["bar_waiting_time"] = plot_metric_bar_comparison(
        metrics, "avg_waiting_time", "Avg Waiting Time (ticks)", output_dir / "bar_waiting_time.png")
    paths["bar_turnaround_time"] = plot_metric_bar_comparison(
        metrics, "avg_turnaround_time", "Avg Turnaround Time (ticks)", output_dir / "bar_turnaround_time.png")
    paths["bar_response_time"] = plot_metric_bar_comparison(
        metrics, "avg_response_time", "Avg Response Time (ticks)", output_dir / "bar_response_time.png")
    paths["bar_context_switches"] = plot_metric_bar_comparison(
        metrics, "context_switches", "Context Switches", output_dir / "bar_context_switches.png")
    paths["bar_throughput"] = plot_metric_bar_comparison(
        metrics, "throughput", "Throughput (proc/tick)", output_dir / "bar_throughput.png")

    paths["radar"] = plot_radar_comparison(metrics, output_dir / "radar_comparison.png")
    paths["heatmap"] = plot_heatmap_comparison(metrics, output_dir / "heatmap_comparison.png")
    paths["pie_context_switch_share"] = plot_context_switch_share_pie(metrics, output_dir / "pie_context_switch_share.png")

    avg_util = float(np.mean([m["cpu_utilization"] for m in metrics.values()])) if metrics else 0.0
    paths["gauge_avg_cpu_utilization"] = plot_cpu_utilization_gauge(
        avg_util, output_dir / "gauge_avg_cpu_utilization.png", title="Avg CPU Utilization (all algorithms)")

    return paths
