"""Complete example with persistence and audit trail.

Demonstrates full system:
1. LLM call
2. Signal detection
3. Control tower decision
4. Enforcement
5. Persistence to audit store
6. Dashboard view
"""

import asyncio
import uuid
from datetime import datetime

from core.interceptor import OllamaInterceptor
from signals.runner import run_signals
from enforcement.control_tower import ControlTower
from contracts.verdict import Verdict, FiredSignal
from persistence.audit_store import AuditStore


async def process_interaction(
    prompt: str,
    model: str = "phi3",
    store: AuditStore = None,
) -> dict:
    """Process a single LLM interaction with full observability.
    
    Args:
        prompt: User prompt
        model: LLM model name
        store: Audit store for persistence
        
    Returns:
        Dictionary with results and metadata
    """
    interaction_id = str(uuid.uuid4())
    
    print(f"\n{'='*70}")
    print(f"INTERACTION: {interaction_id}")
    print(f"{'='*70}\n")
    
    # Step 1: Call LLM
    print("[1/5] Calling LLM...")
    interceptor = OllamaInterceptor()
    llm_response = await interceptor.call(model=model, prompt=prompt)
    
    if llm_response:
        print(f"✅ Response received ({len(llm_response)} chars)\n")
    else:
        print("❌ No response from LLM\n")
        return {"error": "LLM call failed", "interaction_id": interaction_id}
    
    # Step 2: Run signals
    print("[2/5] Running signal detection...")
    signals = run_signals(prompt=prompt, response=llm_response)
    
    failed_signals = [s for s in signals if s.get("value")]
    print(f"✅ Detected {len(failed_signals)} issues\n")
    
    # Step 3: Control tower decision
    print("[3/5] Control Tower evaluating...")
    tower = ControlTower()
    decision = tower.evaluate(signals)
    
    if decision:
        print(f"⚠️  Decision: {decision.action.value.upper()}")
        print(f"   Severity: {decision.severity.value.upper()}")
        print(f"   Reason: {decision.reason}\n")
    else:
        print("✅ Decision: ALLOW (no issues)\n")
    
    # Step 4: Enforcement
    print("[4/5] Applying enforcement...")
    result = tower.enforce(decision, llm_response)
    
    if result['blocked']:
        print("❌ Response BLOCKED\n")
        final_response = None
    else:
        print("✅ Response delivered\n")
        final_response = result['final_response']
    
    # Step 5: Persist to audit store
    if store:
        print("[5/5] Saving to audit store...")
        
        # Convert decision to Verdict object
        if decision:
            verdict = Verdict(
                verdict_id=decision.action.value + "_" + interaction_id[:8],
                severity=decision.severity,
                action=decision.action,
                failure_class=decision.failure_class,
                fired_signals=[FiredSignal(
                    signal_name=decision.failure_class,
                    confidence=decision.confidence,
                    explanation=decision.reason,
                )],
                reason=decision.reason,
                confidence=decision.confidence,
            )
        else:
            verdict = Verdict.create_allow()
        
        store.store_interaction(
            interaction_id=interaction_id,
            prompt=prompt,
            response=final_response,
            verdict=verdict,
            model=model,
        )
        print("✅ Saved to database\n")
    
    print(f"{'='*70}\n")
    
    return {
        "interaction_id": interaction_id,
        "prompt": prompt,
        "response": final_response,
        "blocked": result['blocked'],
        "action": result['action'].value if hasattr(result['action'], 'value') else result['action'],
        "verdict": verdict.to_dict() if decision else None,
    }


async def main():
    """Run complete observability demo."""
    print("\n" + "="*70)
    print("  LLM OBSERVABILITY - Complete System Demo")
    print("="*70)
    
    # Initialize audit store
    store = AuditStore()
    
    # Test prompts
    test_prompts = [
        "Explain RAG in simple terms",
        "What is the capital of France?",
        "Tell me about machine learning",
    ]
    
    results = []
    
    for prompt in test_prompts:
        result = await process_interaction(
            prompt=prompt,
            model="phi3",
            store=store,
        )
        results.append(result)
        
        # Small delay between interactions
        await asyncio.sleep(1)
    
    # Show summary
    print("\n" + "="*70)
    print("  SESSION SUMMARY")
    print("="*70 + "\n")
    
    summary = store.get_summary()
    print(f"Total Interactions: {summary.total_verdicts}")
    print(f"Blocked: {summary.blocked_count}")
    print(f"Warned: {summary.warned_count}")
    print(f"Allowed: {summary.allowed_count}")
    
    if summary.most_fired_signals:
        print("\nMost Fired Signals:")
        for signal, count in sorted(
            summary.most_fired_signals.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  - {signal}: {count} times")
    
    print("\n" + "="*70)
    print("\n👉 View dashboard: python -m dashboard.control_tower_view")
    print("\n" + "="*70 + "\n")
    
    store.close()


if __name__ == "__main__":
    asyncio.run(main())
