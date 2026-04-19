# agent/context.py

from typing import Optional, Set


class AgentContext:
    def __init__(
        self,
        agent_name: str,
        max_steps: int = 5,
        allowed_tool_actions: Optional[Set[str]] = None,
    ):
        self.agent_name = agent_name
        self.max_steps = max_steps
        self.allowed_tool_actions: Optional[frozenset] = (
            frozenset(allowed_tool_actions) if allowed_tool_actions is not None else None
        )

        self.current_step = 0
        self.actions = []

        self.blocked = False
        self.block_reason = None

    def record_action(self, action: str):
        self.current_step += 1
        self.actions.append(action)

    def is_exhausted(self) -> bool:
        return self.current_step >= self.max_steps
