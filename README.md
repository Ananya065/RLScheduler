# CPU Scheduling Simulator &amp; Analysis Platform

A research-grade CPU scheduling simulator covering four classic algorithms —
**FCFS, SJF, Priority, and Round Robin** — with real metrics, matplotlib chart
generation, a PDF report, and a self-contained interactive dashboard.

**No machine learning or reinforcement learning components.** This is a pure
algorithmic scheduling simulator by design.

## Features

- **4 scheduling algorithms**, unmodified core logic, fully deterministic
  (ties broken by `(metric, arrival_time, pid)` — reproducible every run)
- **Benchmark mode**: every algorithm always runs on the identical workload,
  so comparisons are apples-to-apples
- **12 metrics per algorithm**: avg waiting/turnaround/response time, CPU
  utilization, idle time, throughput, context switches, Jain's Fairness
  Index, a starvation heuristic, a composite efficiency score, and simulated
  energy/cache-miss proxies (clearly labeled as simulated)
- **Interactive dashboard** (`dashboard/scheduler_dashboard.html`): sidebar
  navigation, animated Gantt chart with play/pause/step/scrub, live process
  lifecycle lanes, CPU utilization/idle/efficiency gauges, comparison charts
  (bar, radar, pie, heatmap), a process inspector, and CSV/JSON/PNG/PDF export
- **Random workload generator AND custom process input** — both work
  instantly in the dashboard (its own JS scheduling engine, verified against
  the same correctness tests as the Python backend) and via the CLI
- **PDF report generation** (`results/scheduling_report.pdf`) — real
  matplotlib charts embedded via reportlab, one section per algorithm
- **52 automated tests** covering empty workloads, single processes, 1000+
  process workloads, equal priorities, identical arrival times, extreme
  burst times, and invalid input — see [Testing](#testing)

## Installation

```bash
pip install numpy matplotlib reportlab
```

That's the complete dependency list. No GPU, no ML framework, nothing else
required.

## Quick start

```bash
python main.py                                  # random workload, 30 processes
python main.py --n 200 --seed 7 --quantum 4      # bigger workload, custom quantum
python main.py --custom my_processes.json        # your own process list
python main.py --no-pdf                          # skip PDF (faster iteration)
```

Every run prints a CLI comparison table and writes:

| File | Contents |
|---|---|
| `results/metrics_summary.csv` | one row per algorithm, all 12 metrics |
| `results/process_details.csv` | one row per process per algorithm |
| `results/simulation_summary.txt` | human-readable run summary |
| `results/scheduling_report.pdf` | full research-style PDF report |
| `results/charts/*.png` | every chart, individually, as PNG |
| `data/full_simulation.json` | complete per-process detail |
| `data/dashboard_data.json` | same data, shaped for the dashboard |

Then open `dashboard/scheduler_dashboard.html` in any browser — it ships with
a real run already embedded, so it works immediately. Use the sidebar's
"Load JSON" to load a fresh `dashboard_data.json`, or use "Workload Setup" to
generate or type in a new workload directly in the browser.

### Custom workload format

A JSON file for `--custom`:

```json
[
  {"arrival_time": 0, "burst_time": 6, "priority": 1},
  {"arrival_time": 2, "burst_time": 4, "priority": 0},
  {"arrival_time": 4, "burst_time": 9}
]
```

`priority` is optional (defaults to 0). Invalid records (negative times,
missing fields, non-numeric values) raise a clear validation error rather
than silently producing garbage output.

## Testing

```bash
python -m unittest discover -s tests -t . -v
```

52 tests, all currently passing, covering exactly the cases you'd want
checked before trusting this for a report: empty process list, single
process, 1000+ and 2000-process workloads, equal priorities, identical
arrival times, a 500,000-tick burst, negative/zero/non-numeric inputs,
malformed custom-workload files, and invalid Round Robin quantums. See
`tests/test_edge_cases.py` for the exact edge-case list.

The dashboard's JavaScript scheduling engine is separately verified against
the same invariants (see `docs/ARCHITECTURE.md`) — run
`node /tmp/pure_logic.js`-style checks yourself by extracting the engine
functions if you modify them; there's no browser test runner wired in here.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full folder
breakdown, a system flowchart, a class diagram, and a sequence diagram (all
Mermaid, renders directly on GitHub).

## What's a standard metric vs. a designed heuristic

Stated plainly, not smoothed over:

- **Standard, textbook**: avg waiting/turnaround/response time, throughput,
  CPU utilization, Jain's Fairness Index.
- **Designed heuristics, original to this project** — useful for at-a-glance
  comparison, not standard OS formulas: `starvation_score` (how much worse
  off the worst-treated process is vs. average) and
  `scheduling_efficiency_score` (a weighted composite of utilization,
  fairness, and starvation). Both are documented with their exact formula in
  `scheduler/metrics/calculator.py`.
- **Simulated proxies, not real measurements**: `energy_score` and
  `cache_miss_rate`. Real values require actual hardware performance
  counters, which this simulator does not have access to. Labeled as
  "(simulated)" everywhere they're displayed.

## Known limitations

- Single CPU / single ready queue only — no multi-core scheduling.
- No I/O-bound process modeling — every process is a pure CPU burst.
- Burst times are synthetic (uniform distribution), not derived from real
  trace data (e.g. Google Borg, Alibaba Cluster Data).
- PDF export from the dashboard uses the browser's native print-to-PDF; the
  Python-generated `scheduling_report.pdf` (via `python main.py`) is the
  real, chart-embedded report.

## License / attribution

Student/portfolio project scaffold — adapt freely.
