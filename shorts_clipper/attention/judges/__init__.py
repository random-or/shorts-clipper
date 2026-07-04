"""Attention Judges package."""

from shorts_clipper.attention.judges.base import JudgeRegistry, AttentionJudge
from shorts_clipper.attention.judges.cognitive import CuriosityJudge, InformationDensityJudge, PredictionErrorJudge
from shorts_clipper.attention.judges.editorial import ScrollStopJudge, PayoffJudge

__all__ = [
    "JudgeRegistry",
    "AttentionJudge",
    "CuriosityJudge",
    "InformationDensityJudge",
    "PredictionErrorJudge",
    "ScrollStopJudge",
    "PayoffJudge"
]
