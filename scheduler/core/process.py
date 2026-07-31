"""
Core Process model + workload generation.

Two ways to get a workload:
  - generate_processes(...)        random synthetic workload (Poisson arrivals)
  - processes_from_records(...)     custom, user-specified processes

Both funnel through the same Process dataclass and the same validation in
scheduler.utils.validation, so a custom workload is exercised by exactly
the same algorithm code as a random one — no separate code path that could
silently behave differently.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
import numpy as np

from scheduler.utils.validation import (
    validate_process_count,
    validate_custom_processes,
)


@dataclass
class Process:
    pid: int
    arrival_time: int
    burst_time: int
    priority: int = 0

    remaining_time: int = field(default=None)
    waiting_time: int = 0
    turnaround_time: int = 0
    response_time: Optional[int] = None
    completion_time: Optional[int] = None
    first_run_time: Optional[int] = None
    started: bool = False

    execution_history: List[Tuple[int, int]] = field(default_factory=list)

    def __post_init__(self):
        if self.remaining_time is None:
            self.remaining_time = self.burst_time

    def is_complete(self) -> bool:
        return self.remaining_time <= 0

    def reset_runtime_state(self):
        self.remaining_time = self.burst_time
        self.waiting_time = 0
        self.turnaround_time = 0
        self.response_time = None
        self.completion_time = None
        self.first_run_time = None
        self.started = False
        self.execution_history = []

    def record_run(self, start_tick: int, end_tick: int):
        self.execution_history.append((start_tick, end_tick))

    def to_dict(self) -> dict:
        """Serialization for exports / dashboard. Deliberately excludes a
        static `state` field — state is derived live from arrival_time,
        execution_history, and completion_time (see dashboard's
        deriveState()), never stored statically, so it can't go stale."""
        return {
            "pid": self.pid,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "priority": self.priority,
            "waiting_time": self.waiting_time,
            "turnaround_time": self.turnaround_time,
            "response_time": self.response_time,
            "completion_time": self.completion_time,
            "execution_history": self.execution_history,
        }


def generate_processes(
    n: int,
    seed: Optional[int] = None,
    arrival_rate: float = 0.5,
    burst_time_range: tuple = (2, 20),
    priority_range: tuple = (0, 4),
) -> List[Process]:
    """Generate a synthetic workload. Poisson arrivals, uniform burst times.

    Raises ValidationError via validate_process_count if n is invalid.
    n=0 is valid and returns an empty list (calling code / algorithms must
    handle empty workloads gracefully — see tests/test_edge_cases.py).
    """
    validate_process_count(n)
    if n == 0:
        return []

    rng = np.random.default_rng(seed)

    inter_arrival_times = rng.exponential(scale=1.0 / arrival_rate, size=n)
    arrival_times = np.cumsum(inter_arrival_times).astype(int)

    burst_times = rng.integers(burst_time_range[0], burst_time_range[1] + 1, size=n)
    priorities = rng.integers(priority_range[0], priority_range[1] + 1, size=n)

    return [
        Process(
            pid=i,
            arrival_time=int(arrival_times[i]),
            burst_time=int(burst_times[i]),
            priority=int(priorities[i]),
        )
        for i in range(n)
    ]


def processes_from_records(records: List[Dict[str, Any]]) -> List[Process]:
    """Build a workload from user-specified records, e.g.:
        [{"arrival_time": 0, "burst_time": 5, "priority": 1}, ...]
    Validates every record before constructing any Process objects, so a
    bad record anywhere in the list fails loudly instead of partially
    succeeding.
    """
    validate_custom_processes(records)
    return [
        Process(
            pid=i,
            arrival_time=int(r["arrival_time"]),
            burst_time=int(r["burst_time"]),
            priority=int(r.get("priority", 0)),
        )
        for i, r in enumerate(records)
    ]
