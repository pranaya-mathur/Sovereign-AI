from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from rules.verdicts import RuleVerdict


class BaseRule(ABC):
    name: str

    @abstractmethod
    def evaluate(self, signals: List[Dict]) -> Optional[RuleVerdict]:
        """
        Return RuleVerdict if rule fires, else None
        """
        pass
