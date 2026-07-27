"""Canonical resource intelligence for Sprint Whisperer.

No skill-level productivity multipliers live here.  The model prefers measured
per-resource delivery history and otherwise falls back to the resource's own
workbook capacity.  Skill coverage is a feasibility constraint, not an invented
speed penalty.  Estimation reliability is reported separately from delivery rate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.models import ProjectState, Resource, WorkItem


@dataclass(frozen=True)
class ResourceRateEvidence:
    resource_id: str
    daily_rate_hrs: float
    source: str
    sample_size: int
    estimation_reliability: Optional[float]
    skill_match: bool
    sprint_capacity_hrs: float
    committed_hrs: float
    free_capacity_hrs: float


class ResourceIntelligence:
    def __init__(self, state: ProjectState):
        self.state = state

    def sprint(self, sprint_ref: Optional[str]):
        if not sprint_ref:
            return None
        return next((s for s in self.state.sprints
                     if s.sprint_id == sprint_ref or s.sprint_name == sprint_ref), None)

    def resource(self, resource_id: Optional[str]) -> Optional[Resource]:
        if not resource_id:
            return None
        return next((r for r in self.state.team
                     if r.resource_id == resource_id or r.name == resource_id), None)

    def sprint_days(self, sprint_ref: Optional[str]) -> float:
        sprint = self.sprint(sprint_ref)
        if sprint is not None:
            delta = (sprint.end_date - sprint.start_date).total_seconds() / 86400.0
            if delta > 0:
                return delta
        return float(self.state.project_info.sprint_duration_days or 10)

    def effective_capacity_hours(self, resource: Resource, sprint_ref: Optional[str]) -> float:
        return max(0.0, float(resource.daily_capacity_hrs)) * self.sprint_days(sprint_ref) * \
            max(0.0, float(resource.allocation_pct)) * max(0.0, float(resource.availability_pct))

    def committed_hours(self, resource: Resource, sprint_ref: Optional[str],
                        exclude_item_ids: Optional[set[str]] = None) -> float:
        sprint = self.sprint(sprint_ref)
        sprint_name = sprint.sprint_name if sprint else sprint_ref
        excluded = exclude_item_ids or set()
        return sum(
            max(0.0, float(w.remaining_effort_hrs))
            for w in self.state.work_items
            if w.item_id not in excluded
            and w.assigned_resource in {resource.resource_id, resource.name}
            and (not sprint_name or w.assigned_sprint == sprint_name)
        )

    def free_capacity_hours(self, resource: Resource, sprint_ref: Optional[str],
                            exclude_item_ids: Optional[set[str]] = None) -> float:
        return max(0.0, self.effective_capacity_hours(resource, sprint_ref)
                   - self.committed_hours(resource, sprint_ref, exclude_item_ids))

    def _completed_history(self, resource: Resource, required_skill: Optional[str]):
        rows = []
        for w in self.state.work_items:
            if w.assigned_resource not in {resource.resource_id, resource.name}:
                continue
            status = str(getattr(w.status, "value", w.status)).lower()
            if status not in {"done", "completed"}:
                continue
            if required_skill and str(w.required_skill).strip().lower() != str(required_skill).strip().lower():
                continue
            rows.append(w)
        return rows

    def measured_daily_rate(self, resource: Resource, required_skill: Optional[str]) -> tuple[Optional[float], int]:
        """Historical delivered work-units/day, using completed item estimates as work units.

        Actual-vs-estimate variance is deliberately NOT folded into this rate; it is
        estimation reliability and is exposed separately.
        """
        rows = self._completed_history(resource, required_skill)
        if not rows:
            return None, 0
        sprint_names = {w.assigned_sprint for w in rows}
        elapsed_days = sum(self.sprint_days(s) for s in sprint_names)
        if elapsed_days <= 0:
            return None, 0
        delivered = sum(max(0.0, float(w.estimated_effort_hrs)) for w in rows)
        return (delivered / elapsed_days if delivered > 0 else None), len(rows)

    def estimation_reliability(self, resource: Resource, required_skill: Optional[str]) -> Optional[float]:
        rows = [w for w in self._completed_history(resource, required_skill)
                if float(w.actual_effort_hrs) > 0 and float(w.estimated_effort_hrs) > 0]
        if not rows:
            return None
        estimated = sum(float(w.estimated_effort_hrs) for w in rows)
        actual = sum(float(w.actual_effort_hrs) for w in rows)
        if actual <= 0:
            return None
        # 1.0 = aggregate estimate matched actual; lower values mean less reliable.
        return min(estimated, actual) / max(estimated, actual)

    def evidence(self, resource: Resource, item: Optional[WorkItem],
                 sprint_ref: Optional[str]) -> ResourceRateEvidence:
        required_skill = item.required_skill if item else None
        skill_match = (not required_skill) or resource.covers_skill(required_skill)
        measured, n = self.measured_daily_rate(resource, required_skill)
        # Fallback is neutral, resource-specific workbook capacity/day.  No level multiplier.
        capacity_daily = max(0.0, float(resource.daily_capacity_hrs)) * \
            max(0.0, float(resource.allocation_pct)) * max(0.0, float(resource.availability_pct))
        rate = measured if measured is not None else capacity_daily
        # A known mismatch is infeasible for reassignment; do not invent a mismatch penalty.
        if not skill_match:
            rate = 0.0
        cap = self.effective_capacity_hours(resource, sprint_ref)
        committed = self.committed_hours(resource, sprint_ref)
        return ResourceRateEvidence(
            resource_id=resource.resource_id,
            daily_rate_hrs=max(0.0, rate),
            source="individual_history" if measured is not None else "resource_capacity",
            sample_size=n,
            estimation_reliability=self.estimation_reliability(resource, required_skill),
            skill_match=skill_match,
            sprint_capacity_hrs=cap,
            committed_hrs=committed,
            free_capacity_hrs=max(0.0, cap - committed),
        )

    def feasible_receiver(self, resource: Resource, item: WorkItem, sprint_ref: Optional[str],
                          required_hours: Optional[float] = None) -> bool:
        ev = self.evidence(resource, item, sprint_ref)
        need = float(item.remaining_effort_hrs if required_hours is None else required_hours)
        return ev.skill_match and ev.daily_rate_hrs > 0 and ev.free_capacity_hrs >= max(0.0, need)

    def best_receiver(self, item: WorkItem, sprint_ref: Optional[str],
                      exclude_resource_id: Optional[str] = None,
                      required_hours: Optional[float] = None) -> Optional[Resource]:
        candidates = []
        for r in self.state.team:
            if r.resource_id == exclude_resource_id:
                continue
            ev = self.evidence(r, item, sprint_ref)
            need = float(item.remaining_effort_hrs if required_hours is None else required_hours)
            if ev.skill_match and ev.daily_rate_hrs > 0 and ev.free_capacity_hrs >= max(0.0, need):
                candidates.append((ev.daily_rate_hrs, ev.free_capacity_hrs, r.resource_id, r))
        return max(candidates, default=(0, 0, "", None))[-1]
