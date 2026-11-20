import math
import threading
from collections import defaultdict
from typing import List, Dict, Any


class ReinforcementLearningRouter:
    """مسرّع التوجيه الذكي بالتعلم المعزّز (Upper Confidence Bound - UCB1)."""

    def __init__(self, exploration_c: float = 1.2):
        self.c = exploration_c
        self._q_values: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._total_pulls: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def select_agent(self, state_intent: str, candidates: List[str]) -> str:
        if not candidates:
            return "general"
        with self._lock:
            total = self._total_pulls[state_intent]
            for agent in candidates:
                if self._counts[state_intent][agent] == 0:
                    return agent

            best_agent = candidates[0]
            best_ucb = -1e9
            for agent in candidates:
                q = self._q_values[state_intent][agent]
                n = self._counts[state_intent][agent]
                bonus = self.c * math.sqrt(math.log(max(total, 1)) / n)
                ucb = q + bonus
                if ucb > best_ucb:
                    best_ucb = ucb
                    best_agent = agent
            return best_agent

    def update_reward(self, state_intent: str, agent: str, reward: float):
        with self._lock:
            self._total_pulls[state_intent] += 1
            n = self._counts[state_intent][agent] + 1
            self._counts[state_intent][agent] = n
            old_q = self._q_values[state_intent][agent]
            self._q_values[state_intent][agent] = old_q + (reward - old_q) / n

    def policy_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                state: {ag: round(val, 3) for ag, val in agents.items()}
                for state, agents in self._q_values.items()
            }


RL_ROUTER = ReinforcementLearningRouter()
