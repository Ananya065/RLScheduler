"""
Baseline scheduling algorithms: FCFS, SJF (non-preemptive), Priority
(non-preemptive), Round Robin (preemptive).

All algorithms are simulated tick-by-tick (1 time unit per tick) rather than
via event jumps. This is slightly less computationally efficient than a pure
discrete-event simulation, but it makes these baselines directly comparable
to the RL environment in environment.py, which is also tick/step driven.
Once Phase 1 is validated, swapping to an event-driven simulator (e.g. SimPy)
for speed is a safe optimization — the metrics definitions won't change.
"""

from copy import deepcopy
from typing import List, Dict
from process_generator import Process


def _ready_queue(processes: List[Process], current_time: int) -> List[Process]:
    return [p for p in processes if p.arrival_time <= current_time and not p.is_complete()]


def _finalize_metrics(processes: List[Process], end_time: int) -> Dict:
    n = len(processes)
    total_waiting = sum(p.waiting_time for p in processes)
    total_turnaround = sum(p.turnaround_time for p in processes)
    busy_time = sum(p.burst_time for p in processes)

    return {
        "avg_waiting_time": total_waiting / n,
        "avg_turnaround_time": total_turnaround / n,
        "throughput": n / end_time if end_time > 0 else 0.0,
        "cpu_utilization": busy_time / end_time if end_time > 0 else 0.0,
        "total_time": end_time,
        "context_switches": None,  # filled in by algorithms that track it
    }


def simulate_fcfs(processes: List[Process]) -> Dict:
    """Non-preemptive: whichever arrived process is oldest runs to completion."""
    procs = deepcopy(processes)
    for p in procs:
        p.reset_runtime_state()

    t = 0
    context_switches = 0
    last_pid = None
    completed = 0
    n = len(procs)

    while completed < n:
        ready = sorted(_ready_queue(procs, t), key=lambda p: p.arrival_time)
        if not ready:
            t += 1
            continue

        current = ready[0]
        if last_pid is not None and last_pid != current.pid:
            context_switches += 1
        last_pid = current.pid

        if not current.started:
            current.first_run_time = t
            current.started = True

        # run to completion (non-preemptive)
        while current.remaining_time > 0:
            current.remaining_time -= 1
            t += 1
        current.completion_time = t
        current.turnaround_time = current.completion_time - current.arrival_time
        current.waiting_time = current.turnaround_time - current.burst_time
        completed += 1

    metrics = _finalize_metrics(procs, t)
    metrics["context_switches"] = context_switches
    return metrics


def simulate_sjf(processes: List[Process]) -> Dict:
    """Non-preemptive Shortest Job First: among arrived processes, run whichever
    has the smallest total burst time."""
    procs = deepcopy(processes)
    for p in procs:
        p.reset_runtime_state()

    t = 0
    context_switches = 0
    last_pid = None
    completed = 0
    n = len(procs)

    while completed < n:
        ready = _ready_queue(procs, t)
        if not ready:
            t += 1
            continue

        current = min(ready, key=lambda p: (p.burst_time, p.arrival_time))
        if last_pid is not None and last_pid != current.pid:
            context_switches += 1
        last_pid = current.pid

        if not current.started:
            current.first_run_time = t
            current.started = True

        while current.remaining_time > 0:
            current.remaining_time -= 1
            t += 1
        current.completion_time = t
        current.turnaround_time = current.completion_time - current.arrival_time
        current.waiting_time = current.turnaround_time - current.burst_time
        completed += 1

    metrics = _finalize_metrics(procs, t)
    metrics["context_switches"] = context_switches
    return metrics


def simulate_priority(processes: List[Process]) -> Dict:
    """Non-preemptive priority scheduling. Lower `priority` value = runs first.
    Ties broken by arrival time (FCFS)."""
    procs = deepcopy(processes)
    for p in procs:
        p.reset_runtime_state()

    t = 0
    context_switches = 0
    last_pid = None
    completed = 0
    n = len(procs)

    while completed < n:
        ready = _ready_queue(procs, t)
        if not ready:
            t += 1
            continue

        current = min(ready, key=lambda p: (p.priority, p.arrival_time))
        if last_pid is not None and last_pid != current.pid:
            context_switches += 1
        last_pid = current.pid

        if not current.started:
            current.first_run_time = t
            current.started = True

        while current.remaining_time > 0:
            current.remaining_time -= 1
            t += 1
        current.completion_time = t
        current.turnaround_time = current.completion_time - current.arrival_time
        current.waiting_time = current.turnaround_time - current.burst_time
        completed += 1

    metrics = _finalize_metrics(procs, t)
    metrics["context_switches"] = context_switches
    return metrics


def simulate_round_robin(processes: List[Process], quantum: int = 4) -> Dict:
    """Preemptive Round Robin with a fixed time quantum. This is the baseline
    the RL agent's 'dynamically scale the quantum' idea (from the roadmap)
    is specifically trying to outperform."""
    procs = deepcopy(processes)
    for p in procs:
        p.reset_runtime_state()

    n = len(procs)
    procs_by_arrival = sorted(procs, key=lambda p: p.arrival_time)
    t = 0
    completed = 0
    context_switches = 0
    last_pid = None

    queue: List[Process] = []
    arrival_ptr = 0

    def admit_new_arrivals(current_time):
        nonlocal arrival_ptr
        while arrival_ptr < n and procs_by_arrival[arrival_ptr].arrival_time <= current_time:
            queue.append(procs_by_arrival[arrival_ptr])
            arrival_ptr += 1

    admit_new_arrivals(t)

    while completed < n:
        if not queue:
            t += 1
            admit_new_arrivals(t)
            continue

        current = queue.pop(0)

        if last_pid is not None and last_pid != current.pid:
            context_switches += 1
        last_pid = current.pid

        if not current.started:
            current.first_run_time = t
            current.started = True

        run_for = min(quantum, current.remaining_time)
        for _ in range(run_for):
            t += 1
            current.remaining_time -= 1
            admit_new_arrivals(t)  # new processes may arrive mid-slice

        if current.remaining_time > 0:
            queue.append(current)  # goes to back of the queue
        else:
            current.completion_time = t
            current.turnaround_time = current.completion_time - current.arrival_time
            current.waiting_time = current.turnaround_time - current.burst_time
            completed += 1

    metrics = _finalize_metrics(procs, t)
    metrics["context_switches"] = context_switches
    return metrics


ALGORITHMS = {
    "FCFS": simulate_fcfs,
    "SJF": simulate_sjf,
    "Priority": simulate_priority,
    "Round Robin (q=4)": lambda procs: simulate_round_robin(procs, quantum=4),
}


def run_all_baselines(processes: List[Process]) -> Dict[str, Dict]:
    return {name: fn(processes) for name, fn in ALGORITHMS.items()}


if __name__ == "__main__":
    from process_generator import generate_processes

    procs = generate_processes(20, seed=7)
    results = run_all_baselines(procs)
    for name, m in results.items():
        print(f"{name:20s} avg_wait={m['avg_waiting_time']:.2f} "
              f"avg_turnaround={m['avg_turnaround_time']:.2f} "
              f"switches={m['context_switches']}")
