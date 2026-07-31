from .fcfs import simulate_fcfs
from .sjf import simulate_sjf
from .priority import simulate_priority
from .round_robin import simulate_round_robin

ALGORITHM_REGISTRY = {
    "FCFS": simulate_fcfs,
    "SJF": simulate_sjf,
    "Priority": simulate_priority,
    "Round Robin": simulate_round_robin,
}