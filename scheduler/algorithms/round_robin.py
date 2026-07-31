from copy import deepcopy
from typing import List

from scheduler.core.process import Process
from scheduler.algorithms.base import CacheMissTracker, SimResult, empty_result
from scheduler.config import CONFIG
from scheduler.utils.validation import validate_quantum


def simulate_round_robin(processes: List[Process], quantum: int = CONFIG.default_quantum) -> SimResult:
    """Preemptive Round Robin with a fixed time quantum."""
    validate_quantum(quantum)
    if not processes:
        return empty_result(f"Round Robin (q={quantum})")

    procs = deepcopy(processes)
    for p in procs:
        p.reset_runtime_state()

    n = len(procs)
    # deterministic admission order: arrival time, then pid for ties
    procs_by_arrival = sorted(procs, key=lambda p: (p.arrival_time, p.pid))
    t = 0
    completed = 0
    context_switches = 0
    idle_ticks = 0
    last_pid = None
    cache = CacheMissTracker()

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
            idle_ticks += 1
            cache.on_idle_tick()
            admit_new_arrivals(t)
            continue

        current = queue.pop(0)

        if last_pid is not None and last_pid != current.pid:
            context_switches += 1
            cache.on_switch()
        last_pid = current.pid

        if not current.started:
            current.first_run_time = t
            current.response_time = t - current.arrival_time
            current.started = True

        run_for = min(quantum, current.remaining_time)
        run_start = t
        for _ in range(run_for):
            t += 1
            current.remaining_time -= 1
            cache.on_busy_tick()
            admit_new_arrivals(t)
        current.record_run(run_start, t)

        if current.remaining_time > 0:
            queue.append(current)
        else:
            current.completion_time = t
            current.turnaround_time = current.completion_time - current.arrival_time
            current.waiting_time = current.turnaround_time - current.burst_time
            completed += 1

    return SimResult(f"Round Robin (q={quantum})", procs, t, context_switches, idle_ticks, cache.average)
