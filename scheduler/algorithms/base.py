"""
Shared utilities for algorithm implementations: ready-queue lookup, the
cache-miss-rate proxy tracker, and the common SimResult output shape every
algorithm returns.
"""

from dataclasses import dataclass
from typing import List
from scheduler.core.process import Process
from scheduler.config import CONFIG


def ready_queue(processes: List[Process], current_time: int) -> List[Process]:
    return [p for p in processes if p.arrival_time <= current_time and not p.is_complete()]


class CacheMissTracker:
    """Synthetic cache-miss-rate proxy — rises on context switch, decays
    while a process runs uninterrupted or the CPU idles. NOT real hardware
    telemetry; see scheduler/config/settings.py docstring."""

    def __init__(self):
        self.rate = 0.05
        self._sum = 0.0
        self._samples = 0

    def on_switch(self):
        self.rate = min(1.0, self.rate + CONFIG.context_switch_cache_penalty)

    def on_busy_tick(self):
        self.rate = max(0.0, self.rate - CONFIG.cache_decay_per_tick)
        self._sum += self.rate
        self._samples += 1

    def on_idle_tick(self):
        self.rate = max(0.0, self.rate - CONFIG.idle_cache_decay_per_tick)
        self._sum += self.rate
        self._samples += 1

    @property
    def average(self) -> float:
        return self._sum / self._samples if self._samples else 0.0


@dataclass
class SimResult:
    """Uniform output of every algorithm's simulation run. Metrics are
    computed from this afterward (scheduler/metrics/calculator.py) so metric
    definitions live in exactly one place, never duplicated per algorithm."""
    algorithm_name: str
    processes: List[Process]
    total_time: int
    context_switches: int
    idle_ticks: int
    avg_cache_miss_rate: float


def empty_result(algorithm_name: str) -> SimResult:
    """Every algorithm must handle an empty workload the same way: zero
    ticks, zero switches, no processes. Centralized here so that behavior
    can't drift between algorithms."""
    return SimResult(algorithm_name, [], 0, 0, 0, 0.0)
