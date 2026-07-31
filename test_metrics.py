import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler.core.process import generate_processes, processes_from_records
from scheduler.algorithms import ALGORITHM_REGISTRY
from scheduler.metrics.calculator import (
    compute_metrics, compute_all_metrics, jains_fairness_index, starvation_score,
    scheduling_efficiency_score,
)
import numpy as np


def run_algo(name, workload, quantum=4):
    fn = ALGORITHM_REGISTRY[name]
    return fn(workload, quantum=quantum) if name == "Round Robin" else fn(workload)


class TestMetricsEdgeCases(unittest.TestCase):
    def test_empty_workload_metrics_are_well_formed_not_nan(self):
        for name in ALGORITHM_REGISTRY:
            result = run_algo(name, [])
            m = compute_metrics(result)
            for key, value in m.items():
                if isinstance(value, float):
                    self.assertFalse(np.isnan(value), f"{name}.{key} is NaN for empty workload")
            self.assertEqual(m["process_count"], 0)
            self.assertEqual(m["fairness_index"], 1.0)

    def test_single_process_metrics(self):
        workload = generate_processes(1, seed=5)
        for name in ALGORITHM_REGISTRY:
            result = run_algo(name, workload)
            m = compute_metrics(result)
            self.assertEqual(m["avg_waiting_time"], 0.0)
            self.assertEqual(m["fairness_index"], 1.0)
            self.assertEqual(m["context_switches"], 0)

    def test_fairness_index_bounds(self):
        for name in ALGORITHM_REGISTRY:
            workload = generate_processes(40, seed=11)
            result = run_algo(name, workload)
            m = compute_metrics(result)
            self.assertGreaterEqual(m["fairness_index"], 0.0)
            self.assertLessEqual(m["fairness_index"], 1.0 + 1e-9)

    def test_jains_index_perfectly_fair(self):
        values = np.array([5.0, 5.0, 5.0, 5.0])
        self.assertAlmostEqual(jains_fairness_index(values), 1.0)

    def test_jains_index_all_zero_waiting(self):
        values = np.array([0.0, 0.0, 0.0])
        self.assertEqual(jains_fairness_index(values), 1.0)

    def test_starvation_score_zero_when_all_equal(self):
        values = np.array([5.0, 5.0, 5.0])
        self.assertEqual(starvation_score(values), 0.0)

    def test_starvation_score_positive_when_unequal(self):
        values = np.array([1.0, 1.0, 1.0, 100.0])
        self.assertGreater(starvation_score(values), 0.0)

    def test_efficiency_score_finite_and_reasonable_range(self):
        score = scheduling_efficiency_score(cpu_utilization=0.9, fairness=0.8, starvation=0.5)
        self.assertTrue(np.isfinite(score))
        self.assertGreaterEqual(score, 0.0)

    def test_efficiency_score_zero_utilization(self):
        score = scheduling_efficiency_score(cpu_utilization=0.0, fairness=1.0, starvation=0.0)
        self.assertEqual(score, 0.0)

    def test_cpu_utilization_never_exceeds_one(self):
        for name in ALGORITHM_REGISTRY:
            workload = generate_processes(50, seed=21)
            result = run_algo(name, workload)
            m = compute_metrics(result)
            self.assertLessEqual(m["cpu_utilization"], 1.0 + 1e-9)
            self.assertGreaterEqual(m["cpu_utilization"], 0.0)

    def test_idle_plus_busy_equals_total_time(self):
        for name in ALGORITHM_REGISTRY:
            workload = generate_processes(25, seed=8)
            result = run_algo(name, workload)
            busy = sum(p.burst_time for p in result.processes)
            self.assertEqual(busy + result.idle_ticks, result.total_time)

    def test_compute_all_metrics_keys_match_input(self):
        workload = generate_processes(10, seed=1)
        results = {name: run_algo(name, workload) for name in ALGORITHM_REGISTRY}
        metrics = compute_all_metrics(results)
        self.assertEqual(set(metrics.keys()), set(ALGORITHM_REGISTRY.keys()))


if __name__ == "__main__":
    unittest.main()
