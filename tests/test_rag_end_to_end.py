"""End-to-end RAG safety rail verification."""

import pytest
import asyncio
from signals.rag_logic import RAGRail
from enforcement.control_tower_v3 import ControlTowerV3
from contracts.severity_levels import EnforcementAction

@pytest.mark.asyncio
async def test_rag_faithfulness_and_citations():
    rail = RAGRail()
    
    # 1. Test Faithful Response
    context = "The DPDP Act 2023 provides for the protection of digital personal data in India."
    response = "According to the context, the DPDP Act 2023 protects digital personal data in India."
    
    result = rail.check_faithfulness(response, context)
    assert result["status"] == "faithful"
    assert result["score"] >= 0.6
    
    # 2. Test Unfaithful/Hallucinated Response
    hallucination = "The DPDP Act 2023 allows sharing data without any consent with foreign firms."
    result_halluc = rail.check_faithfulness(hallucination, context)
    assert result_halluc["status"] == "unfaithful"
    
    # 3. Test Citations
    cited_res = "The Act defines data fiduciaries [1]. [Source: DPDP Section 2]"
    citations = rail.check_citations(cited_res)
    assert citations["has_citations"] is True
    assert "[1]" in citations["citations_found"]
    assert "[Source: DPDP Section 2]" in citations["citations_found"]

@pytest.mark.asyncio
async def test_control_tower_rag_integration():
    tower = ControlTowerV3()
    
    # Enable RAG in context
    context = {
        "retrieval_context": "Sovereign AI is a safety layer for LLMs developed by the team at Enterprise Guardians.",
        "query": "Who developed Sovereign AI?"
    }
    
    # Faithful response
    good_res = "Sovereign AI was developed by Enterprise Guardians."
    res = tower.evaluate_response(good_res, context)
    assert "rag_faithfulness" in res.metadata
    assert res.metadata["rag_faithfulness"]["status"] == "faithful"
    
    # Unfaithful response (should trigger warning if configured)
    bad_res = "Sovereign AI was developed by OpenAI."
    res_bad = tower.evaluate_response(bad_res, context)
    assert res_bad.metadata["rag_faithfulness"]["status"] == "unfaithful"
    # Note: RAG check is currently configured to WARN if unfaithful in _enrich_result

if __name__ == "__main__":
    asyncio.run(test_rag_faithfulness_and_citations())
    asyncio.run(test_control_tower_rag_integration())
