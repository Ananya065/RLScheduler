from copy import deepcopy
from typing import List

from scheduler.core.process import Process
from scheduler.algorithms.base import ready_queue, CacheMissTracker, SimResult, empty_result


def simulate_sjf(processes: List[Process]) -> SimResult:
    """Non-preemptive Shortest Job First. Ties on (burst_time, arrival_time)
    broken deterministically by pid."""
    if not processes:
        return empty_result("SJF")

    procs = deepcopy(processes)
    for p in procs:
        p.reset_runtime_state()

    t = 0
    context_switches = 0
    idle_ticks = 0
    last_pid = None
    completed = 0
    n = len(procs)
    cache = CacheMissTracker()

    while completed < n:
        ready = ready_queue(procs, t)
        if not ready:
            t += 1
            idle_ticks += 1
            cache.on_idle_tick()
            continue

        current = min(ready, key=lambda p: (p.burst_time, p.arrival_time, p.pid))
        if last_pid is not None and last_pid != current.pid:
            context_switches += 1
            cache.on_switch()
        last_pid = current.pid

        if not current.started:
            current.first_run_time = t
            current.response_time = t - current.arrival_time
            current.started = True

        run_start = t
        while current.remaining_time > 0:
            current.remaining_time -= 1
            t += 1
            cache.on_busy_tick()
        current.record_run(run_start, t)
        current.completion_time = t
        current.turnaround_time = current.completion_time - current.arrival_time
        current.waiting_time = current.turnaround_time - current.burst_time
        completed += 1

    return SimResult("SJF", procs, t, context_switches, idle_ticks, cache.average)
