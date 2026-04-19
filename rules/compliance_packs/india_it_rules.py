"""Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021."""

from typing import Dict, Any, List
import re

def get_it_rules_compliance() -> Dict[str, Any]:
    return {
        "name": "India IT Rules 2021",
        "prohibited_content": [
            "sovereignty_integrity_india",
            "public_order",
            "decency_morality",
            "defamation",
            "incitement_offence"
        ]
    }

class ITRulesChecker:
    """Checker for prohibited content under IT Rules 2021."""
    
    def check_response(self, text: str) -> List[Dict[str, Any]]:
        violations = []
        
        # Rule 3(1)(b) - Prohibited content patterns
        patterns = {
            "Rule 3(1)(b)(i)": r"(belongs to another person.*no right)",
            "Rule 3(1)(b)(ii)": r"(defamatory|obscene|pornographic|paedophilic)",
            "Rule 3(1)(b)(iv)": r"(infringes.*patent|trademark|copyright)",
            "Rule 3(1)(b)(vi)": r"(threatens the unity, integrity, defence, security or sovereignty of India)",
        }
        
        for rule, pattern in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                violations.append({
                    "rule": rule,
                    "severity": "high",
                    "explanation": f"Detected content potentially violating {rule} of IT Rules 2021."
                })
        
        return violations
