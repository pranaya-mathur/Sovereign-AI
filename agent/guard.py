# agent/guard.py

from agent.context import AgentContext


class AgentGuard:
    def check(self, ctx: AgentContext) -> dict:
        if ctx.is_exhausted():
            ctx.blocked = True
            ctx.block_reason = "agent_step_exhaustion"
            return {
                "blocked": True,
                "reason": ctx.block_reason
            }

        if ctx.allowed_tool_actions is not None and ctx.actions:
            last = ctx.actions[-1]
            if last not in ctx.allowed_tool_actions:
                ctx.blocked = True
                ctx.block_reason = "tool_misuse_or_disallowed_action"
                return {"blocked": True, "reason": ctx.block_reason, "action": last}

        return {"blocked": False}
