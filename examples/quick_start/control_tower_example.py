"""Control Tower example - Policy-driven enforcement.

Demonstrates the new Control Tower system with policy-based decisions.
Compare this with ollama_example.py to see the difference.
"""

import asyncio

from core.interceptor import OllamaInterceptor
from signals.runner import run_signals
from enforcement.control_tower import ControlTower


async def main():
    prompt = "Explain RAG in simple terms"

    print("=" * 60)
    print("CONTROL TOWER MODE - Policy-Driven Enforcement")
    print("=" * 60)

    # ---------------------------
    # 1. Call LLM
    # ---------------------------
    print("\n[1] Calling LLM...")
    interceptor = OllamaInterceptor()
    llm_response = await interceptor.call(
        model="phi3",
        prompt=prompt
    )

    print(f"\n[LLM RESPONSE]\n{llm_response}")

    # ---------------------------
    # 2. Run Signals
    # ---------------------------
    print("\n[2] Running signal detection...")
    signals = run_signals(
        prompt=prompt,
        response=llm_response
    )

    print(f"\n[SIGNALS DETECTED]: {len(signals)}")
    for signal in signals:
        status = "🔴 FAIL" if signal.get("value") else "🟢 PASS"
        print(
            f"  {status} {signal['signal']}: "
            f"confidence={signal['confidence']:.2f} - "
            f"{signal['explanation']}"
        )

    # ---------------------------
    # 3. Control Tower Decision
    # ---------------------------
    print("\n[3] Control Tower evaluating policy...")
    tower = ControlTower()
    decision = tower.evaluate(signals)

    if decision:
        print(f"\n[POLICY DECISION]")
        print(f"  Failure Class: {decision.failure_class}")
        print(f"  Severity: {decision.severity.value.upper()}")
        print(f"  Action: {decision.action.value.upper()}")
        print(f"  Confidence: {decision.confidence:.2f}")
        print(f"  Reason: {decision.reason}")
        print(f"  Block: {decision.should_block}")
    else:
        print("\n[POLICY DECISION]: ✅ ALL CLEAR - No action needed")

    # ---------------------------
    # 4. Enforcement
    # ---------------------------
    print("\n[4] Applying enforcement...")
    result = tower.enforce(decision, llm_response)

    print(f"\n[ENFORCEMENT RESULT]")
    print(f"  Action Taken: {result['action'].value.upper()}")
    print(f"  Blocked: {result['blocked']}")
    
    if result['message']:
        print(f"  Message: {result['message']}")

    # ---------------------------
    # 5. Final Output
    # ---------------------------
    print("\n" + "=" * 60)
    if result['blocked']:
        print("❌ RESPONSE BLOCKED")
        print("=" * 60)
        print(f"\nReason: {result.get('reason', 'Policy violation')}")
        print(f"Severity: {result.get('severity', 'unknown').upper()}")
    else:
        print("✅ RESPONSE DELIVERED")
        print("=" * 60)
        print(f"\n{result['final_response']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
