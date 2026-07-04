"""Data models for the Semantic Attention Optimization Engine."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum

class AttentionImpact(Enum):
    """Attention Economy: Attention as a limited resource."""
    ADD = "add"
    PRESERVE = "preserve"
    SPEND = "spend"

class NarrativeState(Enum):
    """Semantic states of a story."""
    SETUP = "setup"
    QUESTION = "question"
    CONFLICT = "conflict"
    ESCALATION = "escalation"
    DISCOVERY = "discovery"
    REVEAL = "reveal"
    PAYOFF = "payoff"
    REFLECTION = "reflection"

@dataclass
class SemanticSegment:
    """A transcript segment mapped to a narrative state."""
    segment: Any # TranscriptSegment
    state: NarrativeState
    is_hook: bool
    is_dead_narrative: bool

@dataclass
class FeatureSet:
    """Centralized feature extraction output. Extracted exactly once."""
    text: str
    word_count: int
    words_per_second: float
    questions: int
    exclamations: int
    emotion_hits: int
    viral_hits: int
    hook_hits: int
    story_arc_markers: int
    contradictions: int
    numbers: int
    money_references: int
    time_references: int
    pause_density: float
    speaker_changes: int
    sentiment: float
    repetition: int
    visual_dependency_markers: int
    raw_words: List[str]
    duration: float
    start_time: float
    end_time: float
    semantic_segments: List[SemanticSegment]

@dataclass
class JudgeResult:
    """Output from a single modular Judge. No silent failures."""
    score: float 
    confidence: Union[float, str]
    reason: str
    signals: List[str]
    evidence: List[str]
    impact: AttentionImpact

@dataclass
class AttentionState:
    """State of attention at a specific segment/second."""
    time: float
    attention_level: float
    gain: float
    loss: float
    predicted_swipe_risk: float
    information_overload: bool
    emotional_intensity: float
    curiosity: float
    reward_expectation: float
    confusion: float
    fatigue: float
    is_spike: bool
    is_valley: bool

@dataclass
class AttentionTimeline:
    """Time-varying attention signal across the entire clip."""
    states: List[AttentionState]
    peak_interest_time: float
    high_risk_moments: List[float]
    boring_regions: List[tuple[float, float]]

@dataclass
class EditorialRecommendation:
    """Exact, quantifiable editorial edits."""
    action: str
    reason: str
    expected_retention_improvement: float
    expected_scroll_stop_improvement: float
    confidence: float
    target_time: Optional[float] = None

@dataclass
class CounterfactualVariant:
    """A simulated clip alternative."""
    variant_id: str
    description: str
    start_time: float
    end_time: float
    modified_segments: List[Any]  # List[TranscriptSegment]

@dataclass
class AttentionReport:
    """Explainable prediction report for a specific variant."""
    start_time: float
    end_time: float
    
    # Core independently estimated metrics (Agent E)
    scroll_stop_prob: float
    retention_3s_prob: float
    completion_prob: float
    payoff_strength: float
    shareability: float
    subscribe_potential: float
    comment_prob: float
    memorability: float
    novelty: float
    curiosity: float
    overall_confidence: Union[float, str]
    
    timeline: AttentionTimeline
    judge_results: Dict[str, JudgeResult] = field(default_factory=dict)
    recommendations: List[EditorialRecommendation] = field(default_factory=list)

@dataclass
class SimulationResult:
    """Final output from Simulation Engine comparing variants."""
    base_variant: CounterfactualVariant
    variants: List[CounterfactualVariant]
    reports: Dict[str, AttentionReport]
    winner_id: str
    reason: str
