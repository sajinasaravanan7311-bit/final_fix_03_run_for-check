"""pm_models.py — Phase 2 PM Decision Intelligence model extensions.

These dataclasses and enums are *additive only*.  They are attached to
Recommendation via the ``pm_intelligence`` field (default=None) so all
existing callers and tests continue to work unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# New enums
# ---------------------------------------------------------------------------

class RecommendationObjective(str, Enum):
    """Primary project management objective this recommendation improves."""
    SCHEDULE_OPTIMIZATION = "Schedule Optimization"
    RISK_MITIGATION = "Risk Mitigation"
    RESOURCE_OPTIMIZATION = "Resource Optimization"
    FORECAST_RELIABILITY = "Forecast Reliability"
    DELIVERY_GOVERNANCE = "Delivery Governance"
    QUALITY_IMPROVEMENT = "Quality Improvement"
    KNOWLEDGE_RESILIENCE = "Knowledge Resilience"
    DELIVERY_CONFIDENCE = "Delivery Confidence"


class RecommendationClassification(str, Enum):
    """Tactical vs. Strategic impact horizon."""
    TACTICAL = "Tactical"
    STRATEGIC = "Strategic"
    HYBRID = "Hybrid"


class ImplementationEffort(str, Enum):
    """Rough effort to implement this recommendation."""
    LOW = "Low"        # < 1 day
    MEDIUM = "Medium"  # 2–3 days
    HIGH = "High"      # 1 sprint


class TriggerReason(str, Enum):
    """Why this recommendation was generated — the detected project signal."""
    CRITICAL_PATH_DEPENDENCY = "Critical Path Dependency"
    RESOURCE_OVERLOAD = "Resource Overload"
    RESOURCE_UNDERUTILIZATION = "Resource Underutilization"
    SINGLE_POINT_OF_FAILURE = "Single Point of Failure"
    HIGH_BLOCKER_EXPOSURE = "High Blocker Exposure"
    SCOPE_VOLATILITY = "Scope Volatility"
    DELIVERY_RISK = "Delivery Risk"
    LOW_FORECAST_CONFIDENCE = "Low Forecast Confidence"
    CAPACITY_IMBALANCE = "Capacity Imbalance"
    RECURRING_BLOCKER = "Recurring Blocker Pattern"
    SKILL_MISMATCH = "Skill Mismatch"
    ESTIMATION_DRIFT = "Estimation Drift"
    REWORK_LOOP = "Rework Loop Detected"
    VELOCITY_DECLINE = "Velocity Decline"
    SPILLOVER_RISK = "Spillover Risk"


# ---------------------------------------------------------------------------
# PM Decision Score — replaces the single delay-reduction number
# ---------------------------------------------------------------------------

@dataclass
class PMDecisionScore:
    """Multi-dimensional scoring that reflects how a PM actually prioritises.

    All sub-scores are normalised 0.0–1.0.
    ``composite`` is the final weighted score used for ranking.
    """
    schedule_benefit: float = 0.0       # delay / OTP improvement
    risk_reduction: float = 0.0         # overall risk delta
    delivery_confidence: float = 0.0    # forecast reliability improvement
    resource_health: float = 0.0        # workload balance / SPOF removal
    governance_improvement: float = 0.0 # review gates, scope freeze, escalation
    implementation_cost: float = 0.0    # 0=cheap, 1=expensive (inverted for ranking)
    urgency: float = 0.0                # overdue multiplier / time-criticality
    composite: float = 0.0              # final weighted score

    def to_dict(self) -> dict:
        return {
            "schedule_benefit": round(self.schedule_benefit, 4),
            "risk_reduction": round(self.risk_reduction, 4),
            "delivery_confidence": round(self.delivery_confidence, 4),
            "resource_health": round(self.resource_health, 4),
            "governance_improvement": round(self.governance_improvement, 4),
            "implementation_cost": round(self.implementation_cost, 4),
            "urgency": round(self.urgency, 4),
            "composite": round(self.composite, 4),
        }


# ---------------------------------------------------------------------------
# Structured PM Explanation
# ---------------------------------------------------------------------------

@dataclass
class PMExplanation:
    """Answers the five PM questions for every recommendation."""
    trigger_reason: TriggerReason
    trigger_detail: str               # one-sentence signal description with data
    primary_objective: RecommendationObjective
    strategic_benefits: List[str]     # bullet-style benefit statements
    ignore_consequence: str           # what happens if PM ignores this
    implementation_effort: ImplementationEffort
    is_immediate_impact: bool         # True=tactical benefit now, False=future sprint
    impact_horizon: str               # "Immediate" | "Next Sprint" | "Long Term"

    def to_dict(self) -> dict:
        return {
            "trigger_reason": self.trigger_reason.value,
            "trigger_detail": self.trigger_detail,
            "primary_objective": self.primary_objective.value,
            "strategic_benefits": self.strategic_benefits,
            "ignore_consequence": self.ignore_consequence,
            "implementation_effort": self.implementation_effort.value,
            "is_immediate_impact": self.is_immediate_impact,
            "impact_horizon": self.impact_horizon,
        }


# ---------------------------------------------------------------------------
# Top-level container attached to Recommendation
# ---------------------------------------------------------------------------

@dataclass
class PMIntelligence:
    """Everything a PM needs to make a smart decision on this recommendation."""
    classification: RecommendationClassification
    pm_decision_score: PMDecisionScore
    explanation: PMExplanation

    def to_dict(self) -> dict:
        return {
            "classification": self.classification.value,
            "pm_decision_score": self.pm_decision_score.to_dict(),
            "explanation": self.explanation.to_dict(),
        }
