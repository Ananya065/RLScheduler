"""
Phase 1 sanity-check script.

Runs all baseline schedulers AND a random-policy pass through the RL
environment on the exact same generated workload, then prints a comparison
table. This is the script you re-run in Phase 2 once you swap the random
policy for your trained PPO agent — if the agent can't beat these numbers,
per the roadmap: it's not ready for Phase 3.
"""

import numpy as np

from process_generator import generate_processes
from baselines import run_all_baselines
from environment import CPUSchedulerEnv


def run_random_policy_in_env(n_processes, seed, n_episodes=5):
    """Average metrics over several episodes since the random policy is
    stochastic — a single run isn't a fair comparison point."""
    waiting_times = []
    context_switches = []
    throughputs = []

    for ep in range(n_episodes):
        env = CPUSchedulerEnv(n_processes=n_processes, seed=seed + ep)
        obs, info = env.reset()
        terminated = truncated = False
        while not (terminated or truncated):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)

        completed = [p for p in env.all_processes if p.is_complete()]
        avg_wait = np.mean([p.waiting_time for p in completed])
        waiting_times.append(avg_wait)
        context_switches.append(env.context_switches)
        throughputs.append(env.completed_count / env.t if env.t > 0 else 0)

    return {
        "avg_waiting_time": float(np.mean(waiting_times)),
        "avg_turnaround_time": None,  # not tracked separately here; wait+burst per process if needed
        "context_switches": float(np.mean(context_switches)),
        "throughput": float(np.mean(throughputs)),
    }


def print_comparison_table(results: dict):
    print(f"\n{'Algorithm':<22}{'Avg Wait':>12}{'Avg Turnaround':>18}{'Context Switches':>20}{'Throughput':>14}")
    print("-" * 86)
    for name, m in results.items():
        turnaround = f"{m['avg_turnaround_time']:.2f}" if m.get('avg_turnaround_time') is not None else "n/a"
        print(f"{name:<22}{m['avg_waiting_time']:>12.2f}{turnaround:>18}"
              f"{m['context_switches']:>20}{m['throughput']:>14.4f}")


if __name__ == "__main__":
    N_PROCESSES = 30
    SEED = 42

    print(f"Generating workload: {N_PROCESSES} processes, seed={SEED}\n")
    procs = generate_processes(N_PROCESSES, seed=SEED)

    print("Running baseline schedulers (FCFS, SJF, Priority, Round Robin)...")
    baseline_results = run_all_baselines(procs)

    print("Running random policy through RL environment (5 episodes, averaged)...")
    random_policy_results = run_random_policy_in_env(N_PROCESSES, seed=SEED)

    all_results = dict(baseline_results)
    all_results["Random Policy (RL env)"] = random_policy_results

    print_comparison_table(all_results)

    print("""
Reading this table:
  - SJF should have the lowest avg waiting time (it's provably optimal for
    average wait among non-preemptive algorithms) — it's your real target
    to beat once you factor in starvation risk, which SJF ignores.
  - Round Robin should have more context switches but fairer waiting times
    across processes (no numeric column for fairness/variance yet — add one
    if you want to track starvation explicitly).
  - Random Policy should currently look BAD (worse than all baselines).
    That's expected — Phase 1's job is just to confirm the environment
    runs correctly end-to-end. In Phase 2, you'll replace random actions
    with a trained PPO agent, and re-run this exact script. Success
    condition for Phase 2: PPO's avg_waiting_time beats Round Robin's,
    ideally approaching SJF's, without SJF's starvation risk.
""")
