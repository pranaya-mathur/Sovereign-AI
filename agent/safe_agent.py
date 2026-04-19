# agent/safe_agent.py

from typing import Optional, Set

from agent.context import AgentContext
from agent.guard import AgentGuard
from core.interceptor import OllamaInterceptor


class SafeAgent:
    def __init__(
        self,
        agent_name: str,
        interceptor: OllamaInterceptor,
        model: str = "phi3:latest",
        allowed_tool_actions: Optional[Set[str]] = None,
    ):
        self.ctx = AgentContext(agent_name, allowed_tool_actions=allowed_tool_actions)
        self.guard = AgentGuard()
        self.interceptor = interceptor
        self.model = model

    async def act(self, prompt: str, action_name: str):
        # record agent action
        self.ctx.record_action(action_name)

        # agent safety check
        guard_result = self.guard.check(self.ctx)
        if guard_result["blocked"]:
            return {
                "status": "blocked",
                "reason": guard_result["reason"],
                "agent": self.ctx.agent_name
            }

        # 🔥 ONLY legal LLM entry point
        text = await self.interceptor.call(
            model=self.model,
            prompt=prompt
        )

        return {
            "status": "allowed",
            "agent": self.ctx.agent_name,
            "step": self.ctx.current_step,
            "response": text
        }
