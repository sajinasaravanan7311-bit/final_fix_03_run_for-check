import { describe, expect, it } from 'vitest'
import { getRecommendationDisplayMetrics, getRecoveryPlanDisplayData } from './normalizers'

describe('getRecommendationDisplayMetrics', () => {
  it('normalizes backend recommendation fields to the UI contract', () => {
    const rec = {
      baseline_probability: 0.42,
      after_probability: 0.68,
      baseline_delay_days: 5.2,
      expected_delay_gain_days: 2.4,
      baseline_risk_score: 70,
      after_risk_score: 55,
      counterfactual_statement: 'Without this action, the project stays at risk.',
    }

    expect(getRecommendationDisplayMetrics(rec, { baseline_deadline_prob: 0.38, baseline_delay: 6.1, baseline_risk: 72 })).toEqual({
      baselineDeadlineProbability: 0.42,
      afterDeadlineProbability: 0.68,
      baselineDelayDays: 5.2,
      expectedDelayGainDays: 2.4,
      baselineRiskScore: 70,
      afterRiskScore: 55,
      counterfactualStatement: 'Without this action, the project stays at risk.',
      delayAttributionSegments: [{ source: 'Direct impact', days: 2.4 }],
    })
  })

  it('derives delay attribution from impact metrics when the backend omits a dedicated field', () => {
    const rec = {
      expected_delay_gain_days: 1.8,
      pm_intelligence: {
        impact_profile: {
          impact_metrics: {
            primary_dimension: 'schedule',
          },
        },
      },
    }

    expect(getRecommendationDisplayMetrics(rec).delayAttributionSegments).toEqual([{ source: 'schedule', days: 1.8 }])
  })
})

describe('getRecoveryPlanDisplayData', () => {
  it('derives recovery-plan display values from the current API response shape', () => {
    const plan = {
      archetype: 'SAFE',
      explanation: {
        narrative_summary: 'Protect the critical path.',
        decision_gates: ['Review staffing at sprint review'],
        success_criteria: ['Stay within budget'],
      },
      score: {
        deadline_probability: 0.74,
        expected_delay_days: 1.8,
        overall_risk_score: 42,
      },
    }

    expect(getRecoveryPlanDisplayData(plan)).toEqual({
      strategicGoal: 'SAFE',
      expectedOutcome: 'Protect the critical path.',
      decisionGates: ['Review staffing at sprint review'],
      successCriteria: ['Stay within budget'],
      baselineDeadlineProbability: null,
      baselineDelayDays: null,
      baselineRiskScore: null,
      forecastConfidence: null,
    })
  })

  it('derives decision gates and success criteria from plan actions when the backend omits them', () => {
    const plan = {
      archetype: 'AGGRESSIVE',
      actions: [{ urgency: 'TODAY' }, { urgency: 'THIS_SPRINT' }],
      explanation: {
        expected_outcome: 'Recover the sprint by closing the critical blockers.',
      },
      score: {
        forecast_confidence: 'HIGH',
      },
    }

    expect(getRecoveryPlanDisplayData(plan)).toEqual({
      strategicGoal: 'AGGRESSIVE',
      expectedOutcome: 'Recover the sprint by closing the critical blockers.',
      decisionGates: ['Confirm immediate actions are started this sprint.', 'Review sprint-level execution at the next review.'],
      successCriteria: ['Recover the sprint by closing the critical blockers.'],
      baselineDeadlineProbability: null,
      baselineDelayDays: null,
      baselineRiskScore: null,
      forecastConfidence: 'HIGH',
    })
  })
})
