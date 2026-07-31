import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler.core.process import generate_processes, processes_from_records
from scheduler.algorithms import ALGORITHM_REGISTRY
from scheduler.algorithms.round_robin import simulate_round_robin
from scheduler.utils.validation import ValidationError


def run_algo(name, workload, quantum=4):
    fn = ALGORITHM_REGISTRY[name]
    return fn(workload, quantum=quantum) if name == "Round Robin" else fn(workload)


class TestAlgorithmInvariants(unittest.TestCase):
    """These invariants must hold for EVERY algorithm on EVERY workload —
    they're checked generically across all four rather than duplicated
    per-algorithm."""

    def _assert_invariants(self, result, workload):
        n = len(workload)
        self.assertEqual(len(result.processes), n)

        for p in result.processes:
            self.assertTrue(p.is_complete(), f"P{p.pid} did not complete")
            self.assertEqual(p.remaining_time, 0)
            self.assertIsNotNone(p.completion_time)
            self.assertGreaterEqual(p.completion_time, p.arrival_time)
            self.assertEqual(p.turnaround_time, p.completion_time - p.arrival_time)
            self.assertEqual(p.waiting_time, p.turnaround_time - p.burst_time)
            self.assertGreaterEqual(p.waiting_time, 0,
                                     f"P{p.pid} has negative waiting time — scheduling bug")
            self.assertIsNotNone(p.response_time)
            self.assertGreaterEqual(p.response_time, 0)
            # sum of execution segments must equal the process's burst time
            total_run = sum(e - s for s, e in p.execution_history)
            self.assertEqual(total_run, p.burst_time,
                              f"P{p.pid} execution history doesn't sum to its burst time")

        self.assertGreaterEqual(result.context_switches, 0)
        self.assertGreaterEqual(result.idle_ticks, 0)
        if n > 0:
            self.assertGreater(result.total_time, 0)

    def test_all_algorithms_on_standard_workload(self):
        workload = generate_processes(30, seed=42)
        for name in ALGORITHM_REGISTRY:
            with self.subTest(algorithm=name):
                result = run_algo(name, workload)
                self._assert_invariants(result, workload)

    def test_all_algorithms_empty_workload(self):
        workload = []
        for name in ALGORITHM_REGISTRY:
            with self.subTest(algorithm=name):
                result = run_algo(name, workload)
                self.assertEqual(result.processes, [])
                self.assertEqual(result.total_time, 0)
                self.assertEqual(result.context_switches, 0)

    def test_all_algorithms_single_process(self):
        workload = generate_processes(1, seed=7)
        for name in ALGORITHM_REGISTRY:
            with self.subTest(algorithm=name):
                result = run_algo(name, workload)
                self._assert_invariants(result, workload)
                self.assertEqual(result.context_switches, 0, "single process should need 0 switches")
                self.assertEqual(result.processes[0].waiting_time, 0,
                                  "the only process should never wait")

    def test_all_algorithms_large_workload_1000(self):
        workload = generate_processes(1000, seed=3)
        for name in ALGORITHM_REGISTRY:
            with self.subTest(algorithm=name):
                result = run_algo(name, workload)
                self._assert_invariants(result, workload)

    def test_equal_priorities_deterministic(self):
        records = [{"arrival_time": 0, "burst_time": 5, "priority": 1} for _ in range(10)]
        workload = processes_from_records(records)
        result_a = run_algo("Priority", workload)
        result_b = run_algo("Priority", workload)
        order_a = [seg[0] for p in sorted(result_a.processes, key=lambda p: p.pid) for seg in p.execution_history]
        order_b = [seg[0] for p in sorted(result_b.processes, key=lambda p: p.pid) for seg in p.execution_history]
        self.assertEqual(order_a, order_b, "equal-priority scheduling must be deterministic")
        self._assert_invariants(result_a, workload)

    def test_same_arrival_times(self):
        records = [{"arrival_time": 0, "burst_time": 4 + i, "priority": i} for i in range(8)]
        workload = processes_from_records(records)
        for name in ALGORITHM_REGISTRY:
            with self.subTest(algorithm=name):
                result = run_algo(name, workload)
                self._assert_invariants(result, workload)

    def test_long_burst_times(self):
        records = [
            {"arrival_time": 0, "burst_time": 100000, "priority": 0},
            {"arrival_time": 5, "burst_time": 3, "priority": 0},
        ]
        workload = processes_from_records(records)
        for name in ALGORITHM_REGISTRY:
            with self.subTest(algorithm=name):
                result = run_algo(name, workload)
                self._assert_invariants(result, workload)

    def test_round_robin_invalid_quantum_raises(self):
        workload = generate_processes(5, seed=1)
        with self.assertRaises(ValidationError):
            simulate_round_robin(workload, quantum=0)
        with self.assertRaises(ValidationError):
            simulate_round_robin(workload, quantum=-2)
        with self.assertRaises(ValidationError):
            simulate_round_robin(workload, quantum=2.5)

    def test_fcfs_orders_by_arrival(self):
        records = [
            {"arrival_time": 5, "burst_time": 2},
            {"arrival_time": 0, "burst_time": 2},
            {"arrival_time": 2, "burst_time": 2},
        ]
        workload = processes_from_records(records)
        result = run_algo("FCFS", workload)
        start_order = sorted(result.processes, key=lambda p: p.execution_history[0][0])
        self.assertEqual([p.pid for p in start_order], [1, 2, 0])  # arrival order: pid1(t=0), pid2(t=2), pid0(t=5)


if __name__ == "__main__":
    unittest.main()
