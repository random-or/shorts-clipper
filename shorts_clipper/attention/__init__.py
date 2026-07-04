"""V3.3 Attention Optimization Engine."""

from shorts_clipper.attention.models import (
    AttentionReport,
    FeatureSet,
    JudgeResult,
    AttentionState,
    AttentionTimeline,
    EditorialRecommendation,
    SimulationResult,
    CounterfactualVariant
)
from shorts_clipper.attention.features import FeatureExtractor
from shorts_clipper.attention.engine import AttentionEngine, SimulationEngine

__all__ = [
    "AttentionReport",
    "FeatureSet",
    "JudgeResult",
    "AttentionState",
    "AttentionTimeline",
    "EditorialRecommendation",
    "SimulationResult",
    "CounterfactualVariant",
    "FeatureExtractor",
    "AttentionEngine",
    "SimulationEngine",
]
