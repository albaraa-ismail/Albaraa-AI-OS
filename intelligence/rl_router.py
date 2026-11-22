import math
import threading
from collections import defaultdict
from typing import Any


class ReinforcementLearningRouter:
    DEFAULT_PRIORS: dict[str, dict[str, float]] = {
        "code": {"code": 0.92, "general": 0.45, "research": 0.25},
        "research": {"research": 0.92, "general": 0.50, "code": 0.20},
        "general": {"general": 0.88, "research": 0.55, "code": 0.35},
    }

    def __init__(self, exploration_c: float = 0.65) -> None:
        self.c = exploration_c
        self._q_values: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._total_pulls: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self._seed_priors()

    def _seed_priors(self) -> None:
        for state, agents in self.DEFAULT_PRIORS.items():
            for agent, score in agents.items():
                self._q_values[state][agent] = score
                self._counts[state][agent] = 2
                self._total_pulls[state] += 2

    def select_agent(self, state_intent: str, candidates: list[str]) -> str:
        if not candidates:
            return "general"
        with self._lock:
            total = max(self._total_pulls[state_intent], 1)
            best_agent = candidates[0]
            best_ucb = -1e9
            for agent in candidates:
                n = self._counts[state_intent][agent]
                q = self._q_values[state_intent][agent] if n > 0 else 0.5
                bonus = self.c * math.sqrt(math.log(total + 1) / max(n, 1))
                ucb = q + bonus
                if ucb > best_ucb:
                    best_ucb = ucb
                    best_agent = agent
            return best_agent

    def update_reward(self, state_intent: str, agent: str, reward: float) -> None:
        with self._lock:
            self._total_pulls[state_intent] += 1
            n = self._counts[state_intent][agent] + 1
            self._counts[state_intent][agent] = n
            old_q = self._q_values[state_intent][agent]
            self._q_values[state_intent][agent] = old_q + (reward - old_q) / n

    def policy_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                state: {ag: round(val, 3) for ag, val in agents.items()}
                for state, agents in self._q_values.items()
            }


RL_ROUTER = ReinforcementLearningRouter()
