"""
Custom Gymnasium environment for RL-based CPU scheduling.

MDP formulation (matches the project roadmap):

  State (S):  [queue_length, avg_burst_time_remaining, cache_miss_rate,
               cpu_utilization, avg_waiting_time]
              All normalized to roughly [0, 1] scale for stable training.

  Action (A): Discrete(MAX_QUEUE). Select which slot in the current ready
              queue (sorted by arrival time, padded with "idle" slots) to
              run next for one quantum. Picking a padding slot = idle tick.

  Reward (R): -(alpha * avg_waiting_time) - (beta * context_switch_penalty)
              + (gamma * throughput), computed as a per-step delta so reward
              is dense rather than sparse (only at episode end).

NOTE on cache_miss_rate: real cache-miss rate would come from hardware
performance counters (via eBPF in Phase 4). In this Phase 1 simulator there
is no real cache, so it's modeled as a synthetic proxy that rises after a
context switch and decays otherwise. This is intentional and documented so
nobody mistakes it for real hardware telemetry later.
"""

from typing import Optional, List
import numpy as np

from gym_compat import Env, Discrete, Box
from process_generator import Process, generate_processes

MAX_QUEUE = 10          # padded ready-queue size = action space size
QUANTUM = 4             # timeslice per dispatch decision, in ticks
ALPHA = 1.0             # waiting-time penalty weight
BETA = 2.0              # context-switch penalty weight
GAMMA = 5.0             # throughput reward weight


class CPUSchedulerEnv(Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        n_processes: int = 20,
        max_queue: int = MAX_QUEUE,
        quantum: int = QUANTUM,
        arrival_rate: float = 0.5,
        burst_time_range: tuple = (2, 20),
        max_ticks: int = 2000,
        seed: Optional[int] = None,
    ):
        super().__init__()
        self.n_processes = n_processes
        self.max_queue = max_queue
        self.quantum = quantum
        self.arrival_rate = arrival_rate
        self.burst_time_range = burst_time_range
        self.max_ticks = max_ticks
        self._seed = seed

        self.action_space = Discrete(max_queue)
        # [queue_length, avg_burst_remaining, cache_miss_rate, cpu_utilization, avg_waiting_time]
        self.observation_space = Box(low=0.0, high=1.0, shape=(5,), dtype=np.float32)

        self.reset(seed=seed)

    # ------------------------------------------------------------------ #
    # Core Gymnasium API
    # ------------------------------------------------------------------ #
    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        if seed is not None:
            self._seed = seed

        self.all_processes: List[Process] = generate_processes(
            self.n_processes,
            seed=self._seed,
            arrival_rate=self.arrival_rate,
            burst_time_range=self.burst_time_range,
        )
        self.t = 0
        self.completed_count = 0
        self.last_pid = None
        self.context_switches = 0
        self.cache_miss_rate = 0.05   # synthetic proxy, starts low
        self.busy_ticks = 0
        self.prev_avg_waiting_time = 0.0
        self.prev_throughput = 0.0

        obs = self._get_observation()
        info = {}
        return obs, info

    def step(self, action: int):
        ready = self._ready_queue()

        reward_context_penalty = 0.0
        idle_tick = False

        if action >= len(ready):
            # Idle action (padding slot, or agent chose to idle) — advance one tick.
            self.t += 1
            idle_tick = True
        else:
            current = ready[action]

            if self.last_pid is not None and self.last_pid != current.pid:
                self.context_switches += 1
                reward_context_penalty = 1.0
                # context switch bumps the synthetic cache-miss proxy
                self.cache_miss_rate = min(1.0, self.cache_miss_rate + 0.15)
            self.last_pid = current.pid

            if not current.started:
                current.first_run_time = self.t
                current.started = True

            run_for = min(self.quantum, current.remaining_time)
            for _ in range(run_for):
                current.remaining_time -= 1
                self.t += 1
                self.busy_ticks += 1
                # cache-miss proxy decays the longer a process runs uninterrupted
                self.cache_miss_rate = max(0.0, self.cache_miss_rate - 0.02)

            if current.remaining_time <= 0:
                current.completion_time = self.t
                current.turnaround_time = current.completion_time - current.arrival_time
                current.waiting_time = current.turnaround_time - current.burst_time
                self.completed_count += 1

        # decay cache miss rate slightly even on idle ticks (nothing thrashing the cache)
        if idle_tick:
            self.cache_miss_rate = max(0.0, self.cache_miss_rate - 0.01)

        terminated = self.completed_count >= self.n_processes
        truncated = self.t >= self.max_ticks

        obs = self._get_observation()
        reward = self._compute_reward(reward_context_penalty)

        info = {
            "t": self.t,
            "completed": self.completed_count,
            "context_switches": self.context_switches,
        }
        return obs, reward, terminated, truncated, info

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _ready_queue(self) -> List[Process]:
        ready = [
            p for p in self.all_processes
            if p.arrival_time <= self.t and not p.is_complete()
        ]
        ready.sort(key=lambda p: p.arrival_time)
        return ready[: self.max_queue]

    def _get_observation(self) -> np.ndarray:
        ready = self._ready_queue()
        queue_length = len(ready) / self.max_queue

        if ready:
            avg_burst_remaining = np.mean([p.remaining_time for p in ready])
            # normalize against the max possible burst time
            avg_burst_remaining = min(1.0, avg_burst_remaining / self.burst_time_range[1])
        else:
            avg_burst_remaining = 0.0

        cpu_utilization = self.busy_ticks / self.t if self.t > 0 else 0.0

        completed = [p for p in self.all_processes if p.is_complete()]
        if completed:
            avg_waiting_time = np.mean([p.waiting_time for p in completed])
            avg_waiting_time_norm = min(1.0, avg_waiting_time / 100.0)  # soft normalization
        else:
            avg_waiting_time_norm = 0.0

        obs = np.array(
            [queue_length, avg_burst_remaining, self.cache_miss_rate,
             cpu_utilization, avg_waiting_time_norm],
            dtype=np.float32,
        )
        return obs

    def _compute_reward(self, context_penalty: float) -> float:
        completed = [p for p in self.all_processes if p.is_complete()]
        avg_waiting_time = np.mean([p.waiting_time for p in completed]) if completed else 0.0
        throughput = self.completed_count / self.t if self.t > 0 else 0.0

        # dense reward = delta in waiting time (want it to decrease) + throughput gain - switch penalty
        delta_wait = self.prev_avg_waiting_time - avg_waiting_time  # positive if wait improved... (see note)
        delta_throughput = throughput - self.prev_throughput

        reward = (
            -ALPHA * (avg_waiting_time - self.prev_avg_waiting_time) * 0.01
            - BETA * context_penalty
            + GAMMA * delta_throughput * 100
        )

        self.prev_avg_waiting_time = avg_waiting_time
        self.prev_throughput = throughput
        return float(reward)

    def render(self):
        ready = self._ready_queue()
        print(f"t={self.t:4d} | ready={len(ready):2d} | completed={self.completed_count}/{self.n_processes} "
              f"| switches={self.context_switches}")


if __name__ == "__main__":
    env = CPUSchedulerEnv(n_processes=15, seed=1)
    obs, info = env.reset()
    print("Initial observation:", obs)

    terminated = truncated = False
    total_reward = 0.0
    steps = 0
    while not (terminated or truncated):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1

    print(f"\nEpisode finished after {steps} decision steps (t={env.t} ticks).")
    print(f"Total reward: {total_reward:.2f}")
    print(f"Completed: {env.completed_count}/{env.n_processes}, "
          f"context switches: {env.context_switches}")
