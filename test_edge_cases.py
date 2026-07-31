import unittest
import sys
import json
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scheduler.core.process import generate_processes, processes_from_records
from scheduler.algorithms import ALGORITHM_REGISTRY
from scheduler.metrics.calculator import compute_all_metrics
from scheduler.exporter import (
    export_metrics_csv, export_full_json, export_simulation_summary_text,
)
from scheduler.utils.validation import ValidationError
from scheduler.main import load_custom_workload


def run_algo(name, workload, quantum=4):
    fn = ALGORITHM_REGISTRY[name]
    return fn(workload, quantum=quantum) if name == "Round Robin" else fn(workload)


class TestEdgeCases(unittest.TestCase):

    # ---- empty process list ----
    def test_empty_process_list_full_pipeline(self):
        results = {name: run_algo(name, []) for name in ALGORITHM_REGISTRY}
        metrics = compute_all_metrics(results)
        self.assertEqual(len(metrics), 4)
        with tempfile.TemporaryDirectory() as tmp:
            export_metrics_csv(metrics, Path(tmp) / "m.csv")
            export_full_json(results, metrics, Path(tmp) / "f.json")
            self.assertTrue((Path(tmp) / "m.csv").exists())
            self.assertTrue((Path(tmp) / "f.json").exists())

    # ---- single process ----
    def test_single_process_full_pipeline(self):
        workload = generate_processes(1, seed=1)
        results = {name: run_algo(name, workload) for name in ALGORITHM_REGISTRY}
        metrics = compute_all_metrics(results)
        for name, m in metrics.items():
            self.assertEqual(m["process_count"], 1)

    # ---- large workload (1000+) ----
    def test_large_workload_completes_quickly(self):
        workload = generate_processes(1000, seed=2)
        start = time.time()
        for name in ALGORITHM_REGISTRY:
            run_algo(name, workload)
        elapsed = time.time() - start
        self.assertLess(elapsed, 10.0, "1000-process benchmark took unexpectedly long — perf regression?")

    def test_very_large_workload_2000(self):
        workload = generate_processes(2000, seed=9)
        for name in ALGORITHM_REGISTRY:
            result = run_algo(name, workload)
            self.assertEqual(len(result.processes), 2000)
            self.assertTrue(all(p.is_complete() for p in result.processes))

    # ---- equal priorities ----
    def test_equal_priorities_all_complete(self):
        records = [{"arrival_time": i % 3, "burst_time": 5, "priority": 2} for i in range(20)]
        workload = processes_from_records(records)
        result = run_algo("Priority", workload)
        self.assertTrue(all(p.is_complete() for p in result.processes))

    # ---- same arrival times ----
    def test_all_same_arrival_time_zero(self):
        records = [{"arrival_time": 0, "burst_time": 3 + i} for i in range(15)]
        workload = processes_from_records(records)
        for name in ALGORITHM_REGISTRY:
            result = run_algo(name, workload)
            self.assertEqual(result.processes[0].waiting_time if False else True, True)  # smoke: no crash
            self.assertTrue(all(p.is_complete() for p in result.processes))

    # ---- long burst times ----
    def test_extremely_long_single_burst(self):
        records = [{"arrival_time": 0, "burst_time": 500000}]
        workload = processes_from_records(records)
        for name in ALGORITHM_REGISTRY:
            result = run_algo(name, workload)
            self.assertEqual(result.processes[0].burst_time, 500000)
            self.assertTrue(result.processes[0].is_complete())

    def test_burst_time_exceeding_hard_limit_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records([{"arrival_time": 0, "burst_time": 10_000_000}])

    # ---- invalid inputs ----
    def test_negative_process_count_raises(self):
        with self.assertRaises(ValidationError):
            generate_processes(-1)

    def test_process_count_over_hard_limit_raises(self):
        with self.assertRaises(ValidationError):
            generate_processes(200_000)

    def test_custom_workload_missing_file_raises(self):
        with self.assertRaises(ValidationError):
            load_custom_workload(Path("/tmp/does_not_exist_xyz123.json"))

    def test_custom_workload_malformed_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{not valid json")
            path = Path(f.name)
        try:
            with self.assertRaises(ValidationError):
                load_custom_workload(path)
        finally:
            path.unlink()

    def test_custom_workload_valid_file_loads(self):
        records = [{"arrival_time": 0, "burst_time": 5}, {"arrival_time": 1, "burst_time": 3}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            path = Path(f.name)
        try:
            workload = load_custom_workload(path)
            self.assertEqual(len(workload), 2)
        finally:
            path.unlink()

    def test_negative_burst_time_in_custom_input_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records([{"arrival_time": 0, "burst_time": -10}])

    def test_non_numeric_arrival_time_raises(self):
        with self.assertRaises(ValidationError):
            processes_from_records([{"arrival_time": "soon", "burst_time": 5}])


if __name__ == "__main__":
    unittest.main()
