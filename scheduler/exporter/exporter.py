"""
CSV, JSON, and dashboard-bundle export. PDF report generation lives in
pdf_report.py (separate file since it has a much heavier dependency —
reportlab + matplotlib chart generation — that CSV/JSON export shouldn't
need to import just to write a spreadsheet row).
"""

import csv
import json
from pathlib import Path
from typing import Dict

from scheduler.algorithms.base import SimResult
from scheduler.utils.logging_config import get_logger

logger = get_logger(__name__)


def export_metrics_csv(metrics: Dict[str, Dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not metrics:
        with open(path, "w", newline="") as f:
            f.write("# no algorithms were run — nothing to export\n")
        logger.warning("export_metrics_csv called with empty metrics dict")
        return path

    fieldnames = list(next(iter(metrics.values())).keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in metrics.values():
            writer.writerow(row)

    logger.info(f"Exported metrics CSV -> {path}")
    return path


def export_process_details_csv(results: Dict[str, SimResult], path: Path) -> Path:
    """Per-process detail (one row per process per algorithm) — useful for
    spreadsheet-side analysis beyond the aggregate metrics summary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["algorithm", "pid", "arrival_time", "burst_time", "priority",
                  "waiting_time", "turnaround_time", "response_time", "completion_time"]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for algo_name, result in results.items():
            for p in result.processes:
                row = p.to_dict()
                row["algorithm"] = algo_name
                writer.writerow({k: row[k] for k in fieldnames})

    logger.info(f"Exported process-detail CSV -> {path}")
    return path


def export_full_json(results: Dict[str, SimResult], metrics: Dict[str, Dict], path: Path) -> Dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "algorithms": {
            name: {"metrics": metrics[name], "processes": [p.to_dict() for p in result.processes]}
            for name, result in results.items()
        }
    }
    with open(path, "w") as f:
        json.dump(bundle, f, indent=2)
    logger.info(f"Exported full simulation JSON -> {path}")
    return bundle


def build_dashboard_bundle(results: Dict[str, SimResult], metrics: Dict[str, Dict], workload_meta: Dict) -> Dict:
    return {
        "meta": workload_meta,
        "algorithms": {
            name: {"metrics": metrics[name], "processes": [p.to_dict() for p in result.processes]}
            for name, result in results.items()
        },
    }


def export_dashboard_json(bundle: Dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(bundle, f, indent=2)
    logger.info(f"Exported dashboard bundle -> {path}")
    return path


def export_simulation_summary_text(metrics: Dict[str, Dict], workload_meta: Dict, path: Path) -> Path:
    """Plain-text simulation summary — quick human-readable record of a run,
    independent of the PDF report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "CPU SCHEDULING SIMULATION SUMMARY",
        "=" * 40,
        f"Processes simulated : {workload_meta.get('n_processes', 'n/a')}",
        f"Random seed          : {workload_meta.get('seed', 'n/a')}",
        f"Round Robin quantum  : {workload_meta.get('quantum', 'n/a')}",
        "",
    ]
    for name, m in metrics.items():
        lines.append(f"[{name}]")
        lines.append(f"  Avg Waiting Time      : {m['avg_waiting_time']:.2f} ticks")
        lines.append(f"  Avg Turnaround Time   : {m['avg_turnaround_time']:.2f} ticks")
        lines.append(f"  Avg Response Time     : {m['avg_response_time']:.2f} ticks")
        lines.append(f"  CPU Utilization       : {m['cpu_utilization']*100:.1f}%")
        lines.append(f"  Idle CPU Time         : {m['idle_cpu_time']} ticks ({m['idle_cpu_percentage']*100:.1f}%)")
        lines.append(f"  Throughput            : {m['throughput']:.4f} proc/tick")
        lines.append(f"  Context Switches      : {m['context_switches']}")
        lines.append(f"  Fairness Index        : {m['fairness_index']:.3f}")
        lines.append(f"  Starvation Score      : {m['starvation_score']:.2f}  (designed heuristic)")
        lines.append(f"  Scheduling Efficiency : {m['scheduling_efficiency_score']:.1f} / 100  (designed heuristic)")
        lines.append(f"  Energy Score (sim)    : {m['energy_score']:.0f} units")
        lines.append(f"  Cache Miss Rate (sim) : {m['cache_miss_rate']*100:.1f}%")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines))
    logger.info(f"Exported simulation summary -> {path}")
    return path
