"""
Shared process model + synthetic workload generator.

Both the baseline schedulers (baselines.py) and the RL environment
(environment.py) simulate the SAME kind of Process objects, generated
the SAME way. This matters: if baselines and the RL env used different
workload assumptions, "the agent beat Round Robin" would be a meaningless
claim. Keep this file as the single source of truth for what a "process"
and "workload" mean in this project.
"""

from dataclasses import dataclass, field
from typing import Optional, List
import numpy as np


@dataclass
class Process:
    pid: int
    arrival_time: int
    burst_time: int          # total CPU time required
    priority: int = 0        # lower number = higher priority (optional, unused by FCFS/RR/SJF)

    # mutable simulation state (filled in as the scheduler runs)
    remaining_time: int = field(default=None)
    waiting_time: int = 0
    turnaround_time: int = 0
    completion_time: Optional[int] = None
    first_run_time: Optional[int] = None
    started: bool = False

    def __post_init__(self):
        if self.remaining_time is None:
            self.remaining_time = self.burst_time

    def is_complete(self) -> bool:
        return self.remaining_time <= 0

    def reset_runtime_state(self):
        """Reset mutable fields so the same Process list can be re-simulated
        under a different scheduling algorithm without regenerating processes."""
        self.remaining_time = self.burst_time
        self.waiting_time = 0
        self.turnaround_time = 0
        self.completion_time = None
        self.first_run_time = None
        self.started = False


def generate_processes(
    n: int,
    seed: Optional[int] = None,
    arrival_rate: float = 0.5,   # avg new-process arrivals per time unit (Poisson)
    burst_time_range: tuple = (2, 20),
    priority_range: tuple = (0, 4),
) -> List[Process]:
    """
    Generate a synthetic batch of n processes.

    Arrival times follow a Poisson process (standard for modeling job
    arrivals — this is also what real cluster traces like Google Borg /
    Alibaba approximate before you swap in the real trace data in a later
    phase). Burst times are drawn uniformly within the given range; swap
    this for an exponential or trace-derived distribution once you're
    validating against real data.
    """
    rng = np.random.default_rng(seed)

    inter_arrival_times = rng.exponential(scale=1.0 / arrival_rate, size=n)
    arrival_times = np.cumsum(inter_arrival_times).astype(int)

    burst_times = rng.integers(burst_time_range[0], burst_time_range[1] + 1, size=n)
    priorities = rng.integers(priority_range[0], priority_range[1] + 1, size=n)

    processes = [
        Process(
            pid=i,
            arrival_time=int(arrival_times[i]),
            burst_time=int(burst_times[i]),
            priority=int(priorities[i]),
        )
        for i in range(n)
    ]
    return processes


if __name__ == "__main__":
    procs = generate_processes(10, seed=42)
    for p in procs:
        print(p)
