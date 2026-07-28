"""
Compatibility shim.

On your machine, `pip install gymnasium` and this file will simply hand off to
the real library — nothing else changes. It exists only because this sandbox
has no network access to install packages, so we needed a way to test the
environment logic locally without gymnasium actually being present.

Do NOT delete this file, but you also don't need to touch it. environment.py
imports from here instead of importing gymnasium directly.
"""

try:
    import gymnasium as gym
    from gymnasium import spaces

    Env = gym.Env
    Discrete = spaces.Discrete
    Box = spaces.Box
    HAVE_REAL_GYMNASIUM = True

except ImportError:
    import numpy as np

    HAVE_REAL_GYMNASIUM = False

    class Discrete:
        def __init__(self, n):
            self.n = n

        def sample(self):
            return np.random.randint(0, self.n)

        def contains(self, x):
            return 0 <= x < self.n

    class Box:
        def __init__(self, low, high, shape=None, dtype=np.float32):
            self.low = low
            self.high = high
            self.shape = shape
            self.dtype = dtype

        def sample(self):
            return np.random.uniform(self.low, self.high, size=self.shape).astype(self.dtype)

    class Env:
        """Minimal stand-in for gymnasium.Env — same method names/signatures
        (reset -> (obs, info), step -> (obs, reward, terminated, truncated, info))
        so your subclass is already Gymnasium-compliant."""

        metadata = {}

        def reset(self, *, seed=None, options=None):
            raise NotImplementedError

        def step(self, action):
            raise NotImplementedError

        def render(self):
            pass

        def close(self):
            pass
