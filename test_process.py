import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler.core.process import Process, generate_processes, processes_from_records
from scheduler.utils.validation import ValidationError


class TestProcessModel(unittest.TestCase):
    def test_process_defaults_remaining_time_to_burst(self):
        p = Process(pid=0, arrival_time=0, burst_time=10)
        self.assertEqual(p.remaining_time, 10)
        self.assertFalse(p.is_complete())

    def test_process_is_complete_when_remaining_zero(self):
        p = Process(pid=0, arrival_time=0, burst_time=5)
        p.remaining_time = 0
        self.assertTrue(p.is_complete())

    def test_reset_runtime_state_restores_remaining_time(self):
        p = Process(pid=0, arrival_time=0, burst_time=5)
        p.remaining_time = 2
        p.waiting_time = 10
        p.execution_history.append((0, 3))
        p.reset_runtime_state()
        self.assertEqual(p.remaining_time, 5)
        self.assertEqual(p.waiting_time, 0)
        self.assertEqual(p.execution_history, [])

    def test_to_dict_does_not_include_static_state_field(self):
        p = Process(pid=0, arrival_time=0, burst_time=5)
        d = p.to_dict()
        self.assertNotIn("state", d)
        self.assertIn("execution_history", d)


class TestGenerateProcesses(unittest.TestCase):
    def test_zero_processes_returns_empty_list(self):
        result = generate_processes(0, seed=1)
        self.assertEqual(result, [])

    def test_negative_count_raises(self):
        with self.assertRaises(ValidationError):
            generate_processes(-5, seed=1)

    def test_non_integer_count_raises(self):
        with self.assertRaises(ValidationError):
            generate_processes(3.5, seed=1)

    def test_deterministic_with_seed(self):
        a = generate_processes(20, seed=99)
        b = generate_processes(20, seed=99)
        self.assertEqual([p.arrival_time for p in a], [p.arrival_time for p in b])
        self.assertEqual([p.burst_time for p in a], [p.burst_time for p in b])

    def test_generated_processes_have_positive_burst_time(self):
        procs = generate_processes(50, seed=1)
        for p in procs:
            self.assertGreater(p.burst_time, 0)
            self.assertGreaterEqual(p.arrival_time, 0)

    def test_large_workload_generation(self):
        procs = generate_processes(1000, seed=1)
        self.assertEqual(len(procs), 1000)
        pids = [p.pid for p in procs]
        self.assertEqual(pids, list(range(1000)))


class TestCustomProcessInput(unittest.TestCase):
    def test_valid_custom_records(self):
        records = [
            {"arrival_time": 0, "burst_time": 5, "priority": 1},
            {"arrival_time": 2, "burst_time": 3},
        ]
        procs = processes_from_records(records)
        self.assertEqual(len(procs), 2)
        self.assertEqual(procs[1].priority, 0)  # default applied

    def test_missing_required_field_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records([{"arrival_time": 0}])  # missing burst_time

    def test_negative_burst_time_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records([{"arrival_time": 0, "burst_time": -5}])

    def test_zero_burst_time_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records([{"arrival_time": 0, "burst_time": 0}])

    def test_negative_arrival_time_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records([{"arrival_time": -1, "burst_time": 5}])

    def test_not_a_list_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records({"arrival_time": 0, "burst_time": 5})


if __name__ == "__main__":
    unittest.main()
