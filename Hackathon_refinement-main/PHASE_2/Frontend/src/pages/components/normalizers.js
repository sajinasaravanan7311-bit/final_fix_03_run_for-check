export function getRecommendationDisplayMetrics(rec = {}, baselineContext = {}) {
  const baselineProbability = rec.baseline_probability ?? rec.baselineDeadlineProbability ?? rec.baseline_deadline_prob ?? baselineContext.baseline_deadline_prob ?? null
  const afterProbability = rec.after_probability ?? rec.afterDeadlineProbability ?? rec.deadline_probability ?? null
  const baselineDelayDays = rec.baseline_delay_days ?? rec.baseline_delay ?? baselineContext.baseline_delay ?? null
  const expectedDelayGainDays = rec.expected_delay_gain_days ?? rec.delay_gain_days ?? null
  const baselineRiskScore = rec.baseline_risk_score ?? rec.baseline_risk ?? baselineContext.baseline_risk ?? null
  const afterRiskScore = rec.after_risk_score ?? rec.overall_risk_score ?? null

  const impactProfile = rec.pm_intelligence?.impact_profile || rec.details?.impact_profile || {}
  const delayAttribution = impactProfile.delay_attribution || impactProfile.impact_metrics?.delay_attribution || null
  const delayAttributionSegments = Array.isArray(delayAttribution) && delayAttribution.length > 0
    ? delayAttribution
    : [
        {
          source: impactProfile.impact_metrics?.primary_dimension || 'Direct impact',
          days: expectedDelayGainDays ?? 0,
        },
      ]

  return {
    baselineDeadlineProbability: baselineProbability,
    afterDeadlineProbability: afterProbability,
    baselineDelayDays,
    expectedDelayGainDays,
    baselineRiskScore,
    afterRiskScore,
    counterfactualStatement: rec.counterfactual_statement ?? rec.counterfactual ?? null,
    delayAttributionSegments,
  }
}

export function getRecoveryPlanDisplayData(plan = {}) {
  const score = plan.score || {}
  const explanation = plan.explanation || {}
  const actions = Array.isArray(plan.actions) ? plan.actions : []
  const expectedOutcome = explanation.expected_outcome ?? explanation.narrative_summary ?? null

  const derivedDecisionGates = explanation.decision_gates?.length
    ? explanation.decision_gates
    : [
        ...(actions.some((action) => action.urgency === 'TODAY') ? ['Confirm immediate actions are started this sprint.'] : []),
        ...(actions.some((action) => action.urgency === 'THIS_SPRINT') ? ['Review sprint-level execution at the next review.'] : []),
        ...(actions.some((action) => action.urgency === 'NEXT_SPRINT') ? ['Reassess readiness before the next planning cycle.'] : []),
      ]

  const derivedSuccessCriteria = explanation.success_criteria?.length
    ? explanation.success_criteria
    : [expectedOutcome || 'Deliver the planned recovery outcome.']

  return {
    strategicGoal: plan.strategic_goal ?? plan.label ?? plan.archetype ?? null,
    expectedOutcome,
    decisionGates: derivedDecisionGates,
    successCriteria: derivedSuccessCriteria,
    baselineDeadlineProbability: score.baseline_deadline_prob ?? null,
    baselineDelayDays: score.baseline_delay ?? null,
    baselineRiskScore: score.baseline_risk ?? null,
    forecastConfidence: score.forecast_confidence ?? score.confidence ?? score.overall_confidence ?? null,
  }
}
