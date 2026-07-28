# RL CPU Scheduler — Phase 1: Simulator & MDP Formulation

Implements Phase 1 of the roadmap: a synthetic workload generator, baseline
schedulers (control group), and a Gymnasium-compatible RL environment.

## Files

- `process_generator.py` — the shared `Process` model + synthetic workload
  generator (Poisson arrivals, uniform burst times). Both baselines and the
  RL env simulate the same kind of workload, generated the same way, so
  comparisons between them are meaningful.
- `baselines.py` — FCFS, SJF, Priority (all non-preemptive), and Round Robin
  (preemptive, configurable quantum). Each returns avg waiting time, avg
  turnaround time, throughput, CPU utilization, and context-switch count.
- `environment.py` — `CPUSchedulerEnv`, a custom Gymnasium environment.
  - **State**: `[queue_length, avg_burst_remaining, cache_miss_rate,
    cpu_utilization, avg_waiting_time]`, each normalized to ~[0, 1].
  - **Action**: `Discrete(MAX_QUEUE)` — pick which ready process to run next
    for one quantum (padding slots = idle).
  - **Reward**: weighted combination of waiting-time penalty, context-switch
    penalty, and throughput reward, computed as a dense per-step signal.
- `main.py` — runs all baselines + a random policy through the environment
  on an identical generated workload and prints a comparison table. This is
  your regression test: re-run it in Phase 2 with your trained agent
  swapped in for the random policy.
- `gym_compat.py` — a compatibility shim. **On your own machine, ignore
  this file** — `pip install gymnasium` and it transparently hands off to
  the real library. It exists only because this sandbox couldn't reach the
  internet to install packages, so the shim let me test the environment
  logic locally without gymnasium actually being present.

## Setup on your machine

```bash
pip install gymnasium numpy
python main.py
```

Once `gymnasium` is installed for real, `gym_compat.py` will detect it via
the `import gymnasium` try-block and use the genuine library automatically —
no code changes needed anywhere else.

## Known simplifications (intentional, for Phase 1)

- `cache_miss_rate` in the state is a **synthetic proxy** (rises after a
  context switch, decays otherwise) — not a real hardware metric. Real
  cache-miss data only becomes available in Phase 4 via eBPF hardware
  counters. Don't treat this number as meaningful outside this simulator.
- Burst times are drawn from a uniform distribution, not from real trace
  data. Swap `process_generator.py`'s distribution for one derived from
  Google Cluster / Alibaba trace data when you get to validating against
  real workloads.
- I/O wait / blocking behavior is not modeled yet — all processes are
  assumed CPU-bound for Phase 1. Add an I/O-wait state to `Process` if your
  project scope requires it.

## What's next (Phase 2, per the roadmap)

1. Install `stable-baselines3` and train a PPO agent against
   `CPUSchedulerEnv`.
2. Re-run `main.py` with the trained agent's policy substituted for the
   random policy — check whether avg waiting time beats Round Robin's.
3. If you see starvation (some processes' `waiting_time` far above average),
   add a scaling penalty to the reward for time spent waiting in the queue,
   as the roadmap describes.
