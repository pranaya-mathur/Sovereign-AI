"""India DPDP Act 2023 Compliance Pack.
Focuses on Chapter II (Obligations of Data Fiduciary) and personal data protection.
"""

from typing import Dict, Any, List
import re

def get_dpdp_compliance_rules() -> Dict[str, Any]:
    return {
        "name": "India DPDP 2023",
        "jurisdiction": "India",
        "critical_patterns": [
            r"aadhaar", r"pan card", r"voter id", r"passport number",
            r"digital personal data", r"consent notice", r"data fiduciary"
        ],
        "mandatory_checks": [
            "pii_leak",
            "consent_verification",
            "child_data_restriction"
        ]
    }

class DPDPChecker:
    """Specialized checker for DPDP violations."""
    
    def check_response_compliance(self, text: str) -> List[Dict[str, Any]]:
        violations = []
        
        # 1. Check for unauthorized PII disclosure
        from rules.pii_india import detect_india_pii
        matches = detect_india_pii(text)
        if matches:
            for m in matches:
                violations.append({
                    "rule": "DPDP_SEC_6_PII_PROTECTION",
                    "severity": "critical",
                    "detected": m.entity_type,
                    "explanation": f"Unauthorized disclosure of {m.entity_type} violates DPDP Sec 6."
                })
        
        return violations
