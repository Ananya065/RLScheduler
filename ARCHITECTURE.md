# Architecture

## Folder structure

```
cpu-scheduler/
├── main.py                        # thin entry point -> scheduler.main.main()
├── scheduler/
│   ├── main.py                     # orchestrator: load/generate workload, run
│   │                                #   benchmark, export everything
│   ├── algorithms/
│   │   ├── base.py                  # ready_queue(), CacheMissTracker, SimResult,
│   │   │                            #   empty_result() — shared by all 4 algorithms
│   │   ├── fcfs.py, sjf.py, priority.py, round_robin.py
│   ├── core/
│   │   └── process.py              # Process dataclass, generate_processes(),
│   │                                #   processes_from_records() (custom input)
│   ├── metrics/
│   │   └── calculator.py           # every metric formula, in one place
│   ├── visualization/
│   │   └── charts.py               # matplotlib chart generation (real data only)
│   ├── exporter/
│   │   ├── exporter.py             # CSV / JSON / text summary export
│   │   └── pdf_report.py           # reportlab PDF report, embeds real charts
│   ├── config/
│   │   └── settings.py             # ALL constants + enums, single source of truth
│   └── utils/
│       ├── validation.py           # input validation, raises ValidationError
│       └── logging_config.py
├── dashboard/
│   └── scheduler_dashboard.html    # self-contained interactive dashboard
├── tests/                          # unittest-based (pytest-compatible) test suite
├── docs/                           # this file, screenshots, etc.
├── data/                           # JSON exports
├── results/                        # CSV/PDF exports + results/charts/ PNGs
└── logs/                           # simulation.log
```

## System flow

```mermaid
flowchart TD
    A["Workload source"] --> A1["Random generator<br/>generate_processes()"]
    A --> A2["Custom input<br/>processes_from_records()"]
    A1 --> V["Input validation<br/>(utils/validation.py)"]
    A2 --> V
    V -->|invalid| E["ValidationError<br/>reported to user, exits cleanly"]
    V -->|valid| B["scheduler.main.run_benchmark()"]

    B --> C1["FCFS"]
    B --> C2["SJF"]
    B --> C3["Priority"]
    B --> C4["Round Robin"]

    C1 & C2 & C3 & C4 --> D["SimResult<br/>(uniform output shape)"]
    D --> M["metrics.calculator.compute_metrics()<br/>waiting/turnaround/response/fairness/<br/>starvation/efficiency/energy/cache-miss"]

    M --> X1["exporter.py<br/>CSV / JSON / summary.txt"]
    M --> X2["visualization/charts.py<br/>matplotlib PNGs"]
    X2 --> X3["pdf_report.py<br/>reportlab PDF"]
    M --> X4["dashboard_data.json"]
    X4 --> DASH["dashboard/scheduler_dashboard.html<br/>(also runs its own JS engine for<br/>live random/custom workloads)"]
```

## Class diagram (core simulation types)

```mermaid
classDiagram
    class Process {
        +int pid
        +int arrival_time
        +int burst_time
        +int priority
        +int remaining_time
        +int waiting_time
        +int turnaround_time
        +int response_time
        +int completion_time
        +List~Tuple~ execution_history
        +is_complete() bool
        +reset_runtime_state()
        +record_run(start, end)
        +to_dict() dict
    }

    class SimResult {
        +str algorithm_name
        +List~Process~ processes
        +int total_time
        +int context_switches
        +int idle_ticks
        +float avg_cache_miss_rate
    }

    class CacheMissTracker {
        +float rate
        +on_switch()
        +on_busy_tick()
        +on_idle_tick()
        +average float
    }

    class SimulationConfig {
        +int default_quantum
        +float context_switch_cache_penalty
        +float energy_per_busy_tick
        +int max_processes_hard_limit
    }

    Process "1" --> "*" Process : execution_history segments
    SimResult "1" --> "*" Process
    SimResult --> CacheMissTracker : produced by
    SimulationConfig ..> CacheMissTracker : configures
```

## Sequence diagram (one benchmark run)

```mermaid
sequenceDiagram
    participant U as User (CLI)
    participant M as scheduler.main
    participant V as utils.validation
    participant A as algorithms.*
    participant Calc as metrics.calculator
    participant Exp as exporter
    participant Viz as visualization.charts
    participant PDF as exporter.pdf_report

    U->>M: python main.py --n 30 --seed 42
    M->>V: validate_process_count(n)
    alt invalid input
        V-->>M: raise ValidationError
        M-->>U: print error, exit 1
    else valid
        V-->>M: ok
        M->>A: generate_processes(n, seed)
        loop for each of FCFS, SJF, Priority, Round Robin
            M->>A: simulate_X(workload)
            A-->>M: SimResult
        end
        M->>Calc: compute_all_metrics(results)
        Calc-->>M: metrics dict
        M->>Exp: export CSV / JSON / summary.txt
        M->>Viz: generate_all_charts(results, metrics)
        Viz-->>M: chart PNG paths
        M->>PDF: generate_pdf_report(...)
        PDF-->>M: scheduling_report.pdf
        M-->>U: print CLI summary table + export paths
    end
```

## Design notes

- **Every algorithm converges on `SimResult`** (`scheduler/algorithms/base.py`) so
  `metrics/calculator.py` has exactly one implementation of "average waiting
  time," "fairness index," etc. — never duplicated per algorithm.
- **The dashboard has its own JavaScript scheduling engine** that mirrors the
  Python algorithms line-for-line (same tie-break rules: `(metric,
  arrival_time, pid)`), verified against the same invariants the Python test
  suite checks (see `tests/`). This lets "Random Workload Generator" and
  "Custom Process Input" run instantly in the browser without a server
  round-trip, while `python main.py` remains the canonical, tested path for
  anything you'd cite in a report.
- **No ML/RL components anywhere in this project.** Four classical algorithms
  only, per project scope.
