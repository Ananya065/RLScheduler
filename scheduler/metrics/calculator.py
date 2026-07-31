"""
All metric definitions live here, computed from real SimResult data.

Two categories, both labeled clearly:
  - Standard, textbook metrics (waiting time, turnaround, response,
    throughput, CPU utilization, Jain's Fairness Index).
  - Designed heuristics, original to this project (starvation_score,
    scheduling_efficiency_score) — useful for at-a-glance comparison, but
    explicitly NOT standard OS textbook metrics. Documented as such wherever
    they appear so nobody mistakes them for established formulas.
"""

from typing import Dict
import numpy as np

from scheduler.algorithms.base import SimResult
from scheduler.config import CONFIG


def _empty_metrics(algorithm_name: str) -> Dict:
    """An empty workload (n=0) is valid input, not an error — return a
    well-formed all-zero metrics dict rather than NaN from numpy operating
    on empty arrays."""
    return {
        "algorithm": algorithm_name,
        "avg_waiting_time": 0.0,
        "avg_turnaround_time": 0.0,
        "avg_response_time": 0.0,
        "throughput": 0.0,
        "cpu_utilization": 0.0,
        "idle_cpu_time": 0,
        "idle_cpu_percentage": 0.0,
        "context_switches": 0,
        "fairness_index": 1.0,
        "starvation_score": 0.0,
        "energy_score": 0.0,
        "cache_miss_rate": 0.0,
        "scheduling_efficiency_score": 0.0,
        "total_time": 0,
        "process_count": 0,
    }


def jains_fairness_index(values: np.ndarray) -> float:
    """Standard Jain's Fairness Index: (sum(x))^2 / (n * sum(x^2)).
    1/n (least fair) to 1 (perfectly fair — every process waited equally).
    Well-established metric from scheduling/networking literature."""
    n = len(values)
    if n == 0 or np.sum(values ** 2) == 0:
        return 1.0
    return float((np.sum(values) ** 2) / (n * np.sum(values ** 2)))


def starvation_score(values: np.ndarray) -> float:
    """DESIGNED heuristic, not a standard metric: how much worse off the
    single worst-treated process is versus the average.
        (max_wait - mean_wait) / mean_wait
    0 = nobody waited longer than average. Higher = investigate for
    starvation — this flags a candidate, it does not prove starvation."""
    if len(values) == 0:
        return 0.0
    mean = np.mean(values)
    if mean == 0:
        return 0.0
    return float((np.max(values) - mean) / mean)


def scheduling_efficiency_score(cpu_utilization: float, fairness: float, starvation: float) -> float:
    """DESIGNED composite heuristic (0-100), original to this project — NOT
    a standard OS metric. Combines three already-computed values into one
    at-a-glance number for the comparison dashboard:

        100 * cpu_utilization * fairness / (1 + starvation)

    Rewards high utilization and fairness; discounted by starvation risk.
    Treat this as a summary indicator to prompt deeper inspection of the
    other metrics — not as a scientific ranking."""
    return float(100 * cpu_utilization * fairness / (1 + starvation))


def compute_metrics(result: SimResult) -> Dict:
    processes = result.processes
    n = len(processes)

    if n == 0:
        return _empty_metrics(result.algorithm_name)

    waiting_times = np.array([p.waiting_time for p in processes], dtype=float)
    turnaround_times = np.array([p.turnaround_time for p in processes], dtype=float)
    response_times = np.array([p.response_time for p in processes], dtype=float)

    busy_ticks = sum(p.burst_time for p in processes)
    total_time = result.total_time
    cpu_utilization = busy_ticks / total_time if total_time > 0 else 0.0
    idle_percentage = result.idle_ticks / total_time if total_time > 0 else 0.0

    fairness = jains_fairness_index(waiting_times)
    starvation = starvation_score(waiting_times)

    energy_score = (
        busy_ticks * CONFIG.energy_per_busy_tick
        + result.context_switches * CONFIG.energy_per_context_switch
    )

    return {
        "algorithm": result.algorithm_name,
        "avg_waiting_time": float(np.mean(waiting_times)),
        "avg_turnaround_time": float(np.mean(turnaround_times)),
        "avg_response_time": float(np.mean(response_times)),
        "throughput": n / total_time if total_time > 0 else 0.0,
        "cpu_utilization": cpu_utilization,
        "idle_cpu_time": result.idle_ticks,
        "idle_cpu_percentage": idle_percentage,
        "context_switches": result.context_switches,
        "fairness_index": fairness,
        "starvation_score": starvation,
        "energy_score": energy_score,
        "cache_miss_rate": result.avg_cache_miss_rate,
        "scheduling_efficiency_score": scheduling_efficiency_score(cpu_utilization, fairness, starvation),
        "total_time": total_time,
        "process_count": n,
    }


def compute_all_metrics(results: Dict[str, SimResult]) -> Dict[str, Dict]:
    return {name: compute_metrics(result) for name, result in results.items()}
