"""pm_explanation_generator.py — Phase 2 PM Decision Intelligence Explanations.

Generates a structured PMExplanation for each Recommendation answering the
five questions a Project Manager needs before acting:

  1. Why am I seeing this?          (trigger_reason + trigger_detail)
  2. What objective does it serve?  (primary_objective)
  3. What value does it provide?    (strategic_benefits)
  4. What if I ignore it?           (ignore_consequence)
  5. How much effort?               (implementation_effort)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.engines.recommendation_engine.models import (
    OpportunitySignal,
    Recommendation,
    RecommendationAction,
    SignalCategory,
    UpstreamEngineOutputs,
    SimulationResult,
    ImpactEstimate,
)
from app.engines.recommendation_engine.pm_decision_scorer import (
    effort_for,
    objective_for,
    trigger_for,
)
from app.engines.recommendation_engine.pm_models import (
    ImplementationEffort,
    PMExplanation,
    RecommendationObjective,
    TriggerReason,
)


# ---------------------------------------------------------------------------
# Strategic-benefit templates per action type
# ---------------------------------------------------------------------------

_STRATEGIC_BENEFITS: Dict[RecommendationAction, List[str]] = {
    RecommendationAction.RESOLVE_BLOCKER: [
        "Removes active impediment to team delivery",
        "Reduces execution risk on affected work items",
        "Restores delivery momentum",
    ],
    RecommendationAction.ESCALATE_BLOCKER_EARLY: [
        "Prevents compounding delay if blocker persists",
        "Reduces blocker exposure for future sprints",
        "Improves stakeholder visibility on delivery risk",
    ],
    RecommendationAction.CROSS_TRAIN_BACKUP: [
        "Removes Single Point of Failure from delivery chain",
        "Improves team resilience and bus-factor",
        "Reduces future sprint delivery risk",
    ],
    RecommendationAction.INSERT_REVIEW_GATE: [
        "Reduces rework and late-stage defect discovery",
        "Improves delivery quality and review coverage",
        "Protects acceptance criteria before handoff",
    ],
    RecommendationAction.FREEZE_SCOPE_REQUEST: [
        "Stabilises current sprint commitments",
        "Prevents scope creep from diluting velocity",
        "Improves forecast reliability for the sprint",
    ],
    RecommendationAction.REBASELINE_ESTIMATE: [
        "Increases forecast accuracy for remaining work",
        "Improves on-time delivery probability",
        "Reduces planning uncertainty for stakeholders",
    ],
    RecommendationAction.APPLY_RAMP_UP_DISCOUNT: [
        "Corrects optimistic velocity assumptions for new team members",
        "Improves sprint plan reliability",
        "Reduces surprise slippage late in the sprint",
    ],
    RecommendationAction.REASSIGN_ITEM: [
        "Improves workload balance across the team",
        "Reduces overload risk on the assigned resource",
        "Improves delivery confidence for the affected item",
    ],
    RecommendationAction.REBALANCE_SPRINT_LOAD: [
        "Distributes capacity risk across more resources",
        "Reduces risk of single resource becoming a bottleneck",
        "Improves team-level throughput",
    ],
    RecommendationAction.ADD_RESOURCE_SKILL: [
        "Closes skill gap blocking critical work",
        "Increases team capacity for the required skill area",
        "Reduces dependency on a single skilled resource",
    ],
    RecommendationAction.PARALLELIZE_ITEMS: [
        "Reduces total elapsed time for independent work",
        "Increases team utilisation",
        "Accelerates critical path completion",
    ],
    RecommendationAction.ADVANCE_ITEM_TO_EARLIER_SPRINT: [
        "Pulls forward high-value delivery",
        "Reduces end-of-project schedule compression",
        "Improves team flow by surfacing blockers earlier",
    ],
    RecommendationAction.PULL_FORWARD_ITEM: [
        "Reduces idle capacity in the current sprint",
        "Improves sprint throughput",
        "Builds ahead of schedule buffer",
    ],
    RecommendationAction.REMOVE_DEPENDENCY_BOTTLENECK: [
        "Unblocks downstream work items in the dependency chain",
        "Reduces critical path length",
        "Improves delivery flow across teams or components",
    ],
    RecommendationAction.SPLIT_ITEM: [
        "Enables partial delivery and earlier feedback",
        "Reduces risk of single large item slipping the sprint",
        "Improves estimation accuracy on smaller units of work",
    ],
    RecommendationAction.SPLIT_AND_PAIR: [
        "Enables parallel execution of split work",
        "Spreads delivery risk across two resources",
        "Accelerates completion while improving review coverage",
    ],
    RecommendationAction.PAIR_REVIEWER: [
        "Improves review quality and reduces knowledge silos",
        "Reduces review cycle time through active pairing",
        "Builds cross-team knowledge for future resilience",
    ],
    RecommendationAction.ASSIGN_AS_SECOND_REVIEWER: [
        "Adds review redundancy to high-risk items",
        "Reduces single-reviewer bottleneck",
        "Improves defect detection before integration",
    ],
    RecommendationAction.RESEQUENCE_NON_CRITICAL_ITEM: [
        "Frees critical path capacity from lower-priority work",
        "Reduces competition for constrained resources",
        "Improves sprint execution focus",
    ],
    RecommendationAction.SWARM_ITEM: [
        "Accelerates a single blocked or at-risk item",
        "Reduces the risk of a single item blocking sprint close",
        "Demonstrates team-level commitment to the sprint goal",
    ],
}


# ---------------------------------------------------------------------------
# Ignore consequence templates per action type
# ---------------------------------------------------------------------------

_IGNORE_CONSEQUENCE: Dict[RecommendationAction, str] = {
    RecommendationAction.RESOLVE_BLOCKER: (
        "Active blocker continues to impact delivery. Blocked items will "
        "accumulate and may spill into the next sprint."
    ),
    RecommendationAction.ESCALATE_BLOCKER_EARLY: (
        "Blocker exposure compounds — later escalation is costlier and "
        "options narrow as the sprint end approaches."
    ),
    RecommendationAction.CROSS_TRAIN_BACKUP: (
        "Critical path remains concentrated on one resource. Any absence "
        "or overload event will have no mitigation path."
    ),
    RecommendationAction.INSERT_REVIEW_GATE: (
        "Review quality risk remains elevated. Defects discovered post-sprint "
        "create rework loops that erode future sprint capacity."
    ),
    RecommendationAction.FREEZE_SCOPE_REQUEST: (
        "Scope volatility continues to dilute team focus and increase "
        "sprint overcommitment risk."
    ),
    RecommendationAction.REBASELINE_ESTIMATE: (
        "Forecast uncertainty remains high. Stakeholders and planning cadence "
        "are working from potentially stale assumptions."
    ),
    RecommendationAction.APPLY_RAMP_UP_DISCOUNT: (
        "Sprint plan remains optimistic for new team members. Actual velocity "
        "shortfall will appear as late-sprint surprise."
    ),
    RecommendationAction.REASSIGN_ITEM: (
        "Resource overload continues, increasing burnout risk and delivery "
        "unreliability for the affected items."
    ),
    RecommendationAction.REBALANCE_SPRINT_LOAD: (
        "Capacity imbalance persists. Bottleneck resource remains a single "
        "point of delivery risk for the sprint."
    ),
    RecommendationAction.ADD_RESOURCE_SKILL: (
        "Skill gap remains open. Work requiring this skill will be delayed "
        "or delivered at lower quality."
    ),
    RecommendationAction.PARALLELIZE_ITEMS: (
        "Work is sequenced unnecessarily. Total elapsed time is longer than "
        "the team's actual capacity requires."
    ),
    RecommendationAction.ADVANCE_ITEM_TO_EARLIER_SPRINT: (
        "High-value item remains queued late. Discovery of blockers is deferred "
        "and schedule buffer erodes."
    ),
    RecommendationAction.PULL_FORWARD_ITEM: (
        "Sprint capacity remains underutilised while future sprints are at risk "
        "of overcommitment."
    ),
    RecommendationAction.REMOVE_DEPENDENCY_BOTTLENECK: (
        "Dependency chain blocks downstream items. Critical path length "
        "grows and schedule risk compounds."
    ),
    RecommendationAction.SPLIT_ITEM: (
        "Large item remains a single delivery risk. If it slips, the entire "
        "sprint commitment is at risk."
    ),
    RecommendationAction.SPLIT_AND_PAIR: (
        "Item remains large and single-threaded. Parallelism opportunity is "
        "missed and review coverage stays low."
    ),
    RecommendationAction.PAIR_REVIEWER: (
        "Knowledge concentration on this work area increases. Future review "
        "capacity depends on a single team member."
    ),
    RecommendationAction.ASSIGN_AS_SECOND_REVIEWER: (
        "Single-reviewer bottleneck continues. Review latency may delay item "
        "completion at sprint close."
    ),
    RecommendationAction.RESEQUENCE_NON_CRITICAL_ITEM: (
        "Non-critical work competes with the critical path for shared resources. "
        "Focus and throughput on critical items is reduced."
    ),
    RecommendationAction.SWARM_ITEM: (
        "At-risk item continues on its current trajectory. If it misses the "
        "sprint, the team's committed scope is incomplete."
    ),
}


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class PMExplanationGenerator:
    """Generate a PMExplanation for a single Recommendation.

    signal_map: signal_id → OpportunitySignal, for trigger detail lookup.
    """

    def __init__(
        self,
        upstream: UpstreamEngineOutputs,
        signal_map: Optional[Dict[str, OpportunitySignal]] = None,
    ) -> None:
        self.upstream = upstream
        self.signal_map = signal_map or {}

    def explain(
        self,
        rec: Recommendation,
        impact: Optional[ImpactEstimate] = None,
        sim: Optional[SimulationResult] = None,
    ) -> PMExplanation:
        action = rec.action_type
        objective = objective_for(action)
        effort = effort_for(action)

        # Detect signal category from metadata or root-cause signal
        signal_category = self._detect_signal_category(rec)
        trigger_reason = trigger_for(signal_category)
        trigger_detail = self._trigger_detail(rec, signal_category, impact, sim)

        strategic_benefits = _STRATEGIC_BENEFITS.get(action, [
            "Reduces project execution risk",
            "Improves delivery predictability",
        ])

        ignore_consequence = _IGNORE_CONSEQUENCE.get(
            action,
            "Risk and uncertainty remain elevated for the affected delivery area.",
        )

        is_immediate = effort in (ImplementationEffort.LOW, ImplementationEffort.MEDIUM)
        if action in {
            RecommendationAction.CROSS_TRAIN_BACKUP,
            RecommendationAction.PAIR_REVIEWER,
            RecommendationAction.ASSIGN_AS_SECOND_REVIEWER,
            RecommendationAction.REBASELINE_ESTIMATE,
            RecommendationAction.APPLY_RAMP_UP_DISCOUNT,
            RecommendationAction.ADD_RESOURCE_SKILL,
        }:
            is_immediate = False

        if is_immediate:
            impact_horizon = "Immediate"
        elif effort == ImplementationEffort.MEDIUM:
            impact_horizon = "Next Sprint"
        else:
            impact_horizon = "Long Term"

        return PMExplanation(
            trigger_reason=trigger_reason,
            trigger_detail=trigger_detail,
            primary_objective=objective,
            strategic_benefits=strategic_benefits,
            ignore_consequence=ignore_consequence,
            implementation_effort=effort,
            is_immediate_impact=is_immediate,
            impact_horizon=impact_horizon,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_signal_category(self, rec: Recommendation) -> Optional[SignalCategory]:
        meta = rec.metadata or {}
        params = meta.get("simulation_params") or {}
        cat_val = params.get("signal_category")
        if cat_val:
            try:
                return SignalCategory(cat_val)
            except ValueError:
                pass
        # Fall back to root-cause signal lookup
        sig = self.signal_map.get(rec.root_cause_signal_id)
        if sig:
            return sig.category
        return None

    def _trigger_detail(
        self,
        rec: Recommendation,
        signal_category: Optional[SignalCategory],
        impact: Optional[ImpactEstimate],
        sim: Optional[SimulationResult],
    ) -> str:
        """Build a one-sentence, data-grounded trigger explanation."""
        action = rec.action_type
        n_items = len(rec.affected_item_ids or [])
        n_resources = len(rec.affected_resource_ids or [])
        n_blockers = len(rec.affected_blocker_ids or [])

        delay_days = 0.0
        if impact:
            delay_days = float(impact.estimated_delay_reduction_days or 0.0)
        otp_gain = 0.0
        if sim:
            otp_gain = float(getattr(sim, "delta_on_time_probability", 0.0) or 0.0)

        # Action-specific rich triggers
        if action == RecommendationAction.CROSS_TRAIN_BACKUP:
            cp_items = len(self.upstream.cp_result.items_on_critical_path or [])
            team_size = max(1, len(rec.affected_resource_ids or [1]))
            return (
                f"{cp_items} critical path items currently have no backup coverage. "
                f"A single resource absence would stall delivery with no mitigation."
            )
        if action == RecommendationAction.RESOLVE_BLOCKER:
            return (
                f"{n_blockers} active blocker(s) are impeding {n_items} work item(s). "
                + (f"Resolving this could save up to {delay_days:.1f} days." if delay_days > 0 else
                   "Resolving this removes the immediate impediment to team progress.")
            )
        if action == RecommendationAction.REBASELINE_ESTIMATE:
            return (
                "Current estimates show significant deviation from actuals. "
                "Rebaselining will improve forecast accuracy and stakeholder confidence."
            )
        if action == RecommendationAction.FREEZE_SCOPE_REQUEST:
            return (
                "Scope additions in recent sprints are increasing commitment risk. "
                "A scope freeze protects the current sprint plan."
            )
        if action in {RecommendationAction.INSERT_REVIEW_GATE, RecommendationAction.PAIR_REVIEWER,
                      RecommendationAction.ASSIGN_AS_SECOND_REVIEWER}:
            return (
                f"{n_items} item(s) are approaching completion without sufficient review coverage. "
                "Adding a review step reduces late-stage defect risk."
            )
        if action in {RecommendationAction.REASSIGN_ITEM, RecommendationAction.REBALANCE_SPRINT_LOAD}:
            return (
                f"{n_resources} resource(s) show capacity imbalance. "
                "Redistribution improves team-level throughput and reduces overload risk."
            )
        if action == RecommendationAction.ADD_RESOURCE_SKILL:
            return (
                f"A skill gap is blocking {n_items} item(s) from progressing. "
                "Adding the required capability removes the execution constraint."
            )
        if action in {RecommendationAction.PARALLELIZE_ITEMS, RecommendationAction.SPLIT_ITEM,
                      RecommendationAction.SPLIT_AND_PAIR}:
            return (
                f"{n_items} item(s) can be parallelised or split to reduce elapsed time. "
                + (f"Expected to save {delay_days:.1f} days of delivery time." if delay_days > 0 else
                   "Improves sprint throughput without adding scope.")
            )
        if action == RecommendationAction.REMOVE_DEPENDENCY_BOTTLENECK:
            return (
                "A dependency bottleneck is blocking downstream work in the critical chain. "
                "Removing it reduces schedule risk and unlocks parallel delivery."
            )
        # Generic fallback with OTP gain if available
        if otp_gain > 0:
            return (
                f"Project signals indicate a delivery risk that this action can reduce. "
                f"Estimated on-time probability improvement: +{otp_gain*100:.1f}%."
            )
        return (
            f"Project signals indicate elevated risk across {n_items} work item(s). "
            "This action directly addresses the identified risk pattern."
        )
