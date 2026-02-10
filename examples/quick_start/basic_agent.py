# examples/quick_start/basic_agent.py

import asyncio

from core.interceptor import OllamaInterceptor
from agent.safe_agent import SafeAgent


async def main():
    interceptor = OllamaInterceptor()
    agent = SafeAgent(
        agent_name="retrieval_agent",
        interceptor=interceptor,
        model="phi3:latest"
    )

    result = await agent.act(
        prompt="Explain RAG in GenAI",
        action_name="initial_query"
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())
