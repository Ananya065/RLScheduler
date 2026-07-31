"""
Algorithm registry — the four classic scheduling algorithms this project
covers. Add a new algorithm module and register it here to have it
automatically appear in benchmarks, exports, and the dashboard.

No ML/RL policies are included in this project by design.
"""

from scheduler.algorithms.fcfs import simulate_fcfs
from scheduler.algorithms.sjf import simulate_sjf
from scheduler.algorithms.priority import simulate_priority
from scheduler.algorithms.round_robin import simulate_round_robin

ALGORITHM_REGISTRY = {
    "FCFS": simulate_fcfs,
    "SJF": simulate_sjf,
    "Priority": simulate_priority,
    "Round Robin": simulate_round_robin,
}
