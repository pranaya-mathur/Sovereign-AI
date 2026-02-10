import asyncio

from core.interceptor import OllamaInterceptor
from signals.runner import run_signals
from rules.engine import evaluate_rules
from rules.verdict_reducer import reduce_verdicts
from enforcement.enforcer import ActionEnforcer


async def main():
    prompt = "Explain RAG in simple terms"

    # ---------------------------
    # 1. Call LLM
    # ---------------------------
    interceptor = OllamaInterceptor()
    llm_response = await interceptor.call(
        model="phi3",
        prompt=prompt
    )

    print("\nRAW LLM RESPONSE:\n", llm_response)

    # ---------------------------
    # 2. Run Signals (FUNCTION)
    # ---------------------------
    signals = run_signals(
        prompt=prompt,
        response=llm_response
    )

    for s in signals:
        print("SIGNAL:", s)

    # ---------------------------
    # 3. Run Rules (FUNCTION)
    # ---------------------------
    verdicts = evaluate_rules(signals)

    for v in verdicts:
        print("VERDICT:", v)

    # ---------------------------
    # 4. Reduce Verdicts
    # ---------------------------
    final_verdict = reduce_verdicts(verdicts)
    print("\nFINAL VERDICT:", final_verdict)

    # ---------------------------
    # 5. Enforce Action
    # ---------------------------
    enforcer = ActionEnforcer()
    final_output = enforcer.enforce(
        rule_verdict=final_verdict,
        llm_response=llm_response
    )

    print("\nACTION:", final_output["action"])
    print("\nFINAL RESPONSE:\n", final_output["final_response"])


if __name__ == "__main__":
    asyncio.run(main())
