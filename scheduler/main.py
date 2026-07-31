"""
Orchestrator: generate (or load) one workload, run every registered
algorithm against it — this IS benchmark mode, since all four algorithms
always run together on the identical workload for a fair comparison —
compute metrics, export CSV/JSON/summary/PDF, print a CLI table.

Usage:
    python main.py                                   # random workload
    python main.py --n 200 --seed 7 --quantum 4
    python main.py --custom my_processes.json         # user-specified processes
    python main.py --no-pdf                           # skip PDF (faster)
"""

import argparse
import json
import sys
from pathlib import Path

from scheduler.core.process import generate_processes, processes_from_records
from scheduler.algorithms import ALGORITHM_REGISTRY
from scheduler.metrics.calculator import compute_all_metrics
from scheduler.exporter import (
    export_metrics_csv,
    export_process_details_csv,
    export_full_json,
    build_dashboard_bundle,
    export_dashboard_json,
    export_simulation_summary_text,
    generate_pdf_report,
)
from scheduler.utils.logging_config import get_logger
from scheduler.utils.validation import ValidationError

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
CHARTS_DIR = RESULTS_DIR / "charts"


def load_custom_workload(path: Path):
    """Load a custom process list from a JSON file:
        [{"arrival_time": 0, "burst_time": 5, "priority": 1}, ...]
    Raises ValidationError (caught at CLI boundary) on malformed input."""
    if not path.exists():
        raise ValidationError(f"Custom workload file not found: {path}")
    try:
        records = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValidationError(f"Custom workload file is not valid JSON: {e}")
    return processes_from_records(records)


def run_benchmark(workload, quantum: int):
    """Run every registered algorithm on the identical workload — this is
    benchmark mode. Returns (results, metrics) dicts keyed by algorithm name."""
    results = {}
    for name, fn in ALGORITHM_REGISTRY.items():
        logger.info(f"Running {name}...")
        results[name] = fn(workload, quantum=quantum) if name == "Round Robin" else fn(workload)

    metrics = compute_all_metrics(results)
    return results, metrics


def print_summary(metrics: dict):
    if not metrics:
        print("\n(no results to display)")
        return

    header = (f"{'Algorithm':<16}{'AvgWait':>9}{'AvgTAT':>9}{'AvgResp':>9}"
              f"{'Fairness':>10}{'Starve':>8}{'Effic.':>8}{'Switch':>8}{'CPU%':>7}{'Idle%':>7}")
    print("\n" + header)
    print("-" * len(header))
    for name, m in metrics.items():
        print(
            f"{name:<16}{m['avg_waiting_time']:>9.2f}{m['avg_turnaround_time']:>9.2f}"
            f"{m['avg_response_time']:>9.2f}{m['fairness_index']:>10.3f}"
            f"{m['starvation_score']:>8.2f}{m['scheduling_efficiency_score']:>8.1f}"
            f"{m['context_switches']:>8}{m['cpu_utilization']*100:>7.1f}"
            f"{m['idle_cpu_percentage']*100:>7.1f}"
        )


def main():
    parser = argparse.ArgumentParser(description="CPU Scheduling Simulator & Analysis Platform")
    parser.add_argument("--n", type=int, default=30, help="number of processes (random workload)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quantum", type=int, default=4, help="Round Robin time quantum")
    parser.add_argument("--custom", type=str, default=None,
                         help="path to a JSON file of custom process records, overrides --n")
    parser.add_argument("--no-pdf", action="store_true", help="skip PDF report generation (faster)")
    parser.add_argument("--out-dir", type=str, default=None, help="override output root directory")
    args = parser.parse_args()

    out_root = Path(args.out_dir) if args.out_dir else PROJECT_ROOT
    data_dir = out_root / "data"
    results_dir = out_root / "results"
    charts_dir = results_dir / "charts"

    try:
        if args.custom:
            workload = load_custom_workload(Path(args.custom))
            workload_meta = {"n_processes": len(workload), "seed": None, "quantum": args.quantum,
                              "source": f"custom:{args.custom}"}
        else:
            workload = generate_processes(args.n, seed=args.seed)
            workload_meta = {"n_processes": args.n, "seed": args.seed, "quantum": args.quantum,
                              "source": "random"}
    except ValidationError as e:
        print(f"Input error: {e}", file=sys.stderr)
        sys.exit(1)

    results, metrics = run_benchmark(workload, args.quantum)
    print_summary(metrics)

    export_metrics_csv(metrics, results_dir / "metrics_summary.csv")
    export_process_details_csv(results, results_dir / "process_details.csv")
    export_full_json(results, metrics, data_dir / "full_simulation.json")
    export_simulation_summary_text(metrics, workload_meta, results_dir / "simulation_summary.txt")

    bundle = build_dashboard_bundle(results, metrics, workload_meta)
    export_dashboard_json(bundle, data_dir / "dashboard_data.json")

    print(f"\nExports written to {results_dir} and {data_dir}:")
    print(f"  metrics_summary.csv")
    print(f"  process_details.csv")
    print(f"  simulation_summary.txt")
    print(f"  full_simulation.json")
    print(f"  dashboard_data.json  <- load this in dashboard/scheduler_dashboard.html")

    if not args.no_pdf:
        pdf_path = generate_pdf_report(results, metrics, workload_meta,
                                        results_dir / "scheduling_report.pdf", chart_dir=charts_dir)
        print(f"  scheduling_report.pdf")
    else:
        print("  (PDF report skipped: --no-pdf)")


if __name__ == "__main__":
    main()
