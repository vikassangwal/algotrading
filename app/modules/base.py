"""Base contract for all analysis modules."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..data.provider import DataProvider


@dataclass
class ModuleSignal:
    module: str
    score: float          # -1 (strong sell) .. +1 (strong buy)
    confidence: float     # 0 .. 1 — how much the module trusts its own read
    reasons: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.score = max(-1.0, min(1.0, self.score))
        self.confidence = max(0.0, min(1.0, self.confidence))


class AnalysisModule(ABC):
    name: str = "base"

    def __init__(self, provider: DataProvider):
        self.provider = provider

    @abstractmethod
    def analyze(self, symbol: str) -> ModuleSignal: ...
