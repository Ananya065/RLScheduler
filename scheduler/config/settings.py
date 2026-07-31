"""
Central configuration — every constant used anywhere in the simulator
lives here. If you need to tune the simulation, this is the only file
you should have to touch.
"""

from dataclasses import dataclass
from enum import Enum


class ProcessState(str, Enum):
    """Lifecycle states used by the process-state timeline / dashboard lanes.

    NOTE: this simulator is CPU-bound only — no I/O-blocking is modeled.
    WAITING therefore means "in the ready queue, not on the CPU right now",
    not "blocked on I/O". If you add I/O bursts later, split this into
    READY (waiting for CPU) and BLOCKED (waiting on I/O) instead of
    overloading WAITING.
    """
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TERMINATED = "TERMINATED"


class AlgorithmName(str, Enum):
    FCFS = "FCFS"
    SJF = "SJF"
    PRIORITY = "Priority"
    ROUND_ROBIN = "Round Robin"


@dataclass(frozen=True)
class SimulationConfig:
    """Simulation-wide constants."""

    default_quantum: int = 4
    max_ready_queue_display: int = 10   # dashboard display cap, not a simulation limit

    # Synthetic proxy for cache-miss rate — NOT real hardware telemetry.
    # Rises after a context switch (real switches do flush cache lines on
    # real hardware), decays while a process runs uninterrupted.
    context_switch_cache_penalty: float = 0.15
    cache_decay_per_tick: float = 0.02
    idle_cache_decay_per_tick: float = 0.01

    # Simulated energy-cost model — illustrative units, not calibrated to
    # any real processor's power draw.
    energy_per_busy_tick: float = 1.0
    energy_per_context_switch: float = 3.0

    # Workload generation defaults
    default_arrival_rate: float = 0.5          # Poisson arrivals/tick
    default_burst_time_range: tuple = (2, 20)
    default_priority_range: tuple = (0, 4)
    random_seed_default: int = 42

    # Validation bounds — reject nonsensical input rather than silently
    # producing garbage results.
    max_processes_hard_limit: int = 100_000
    max_burst_time: int = 1_000_000
    max_arrival_time: int = 1_000_000


CONFIG = SimulationConfig()
