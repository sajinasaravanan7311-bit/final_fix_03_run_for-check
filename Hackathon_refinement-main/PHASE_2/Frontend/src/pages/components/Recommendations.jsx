import React, { useState, useEffect } from 'react'
import { api } from '../../api/client'
import { getRecommendationDisplayMetrics } from './normalizers'

function IntentBadge({ intent }) {
  const map = {
    RECOVER: { color: 'var(--red)', bg: 'color-mix(in srgb, var(--red) 16%, transparent)' },
    PROTECT: { color: 'var(--teal)', bg: 'color-mix(in srgb, var(--teal) 16%, transparent)' },
    PREPARE: { color: 'var(--purple)', bg: 'color-mix(in srgb, var(--purple) 16%, transparent)' },
    STABILIZE: { color: 'var(--yellow)', bg: 'color-mix(in srgb, var(--yellow) 16%, transparent)' },
  }
  const style = map[intent] || map.PROTECT
  return (
    <span style={{ borderRadius: 3, padding: '3px 5px', fontSize: 8, fontWeight: 800, textTransform: 'uppercase', color: style.color, background: style.bg, display: 'inline-block' }}>
      {intent || 'PROTECT'}
    </span>
  )
}

function MetricTile({ label, value, mono }) {
  return (
    <div style={{ border: '1px solid var(--line2)', borderRadius: 5, padding: '7px 8px' }}>
      <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase', letterSpacing: '.08em' }}>{label}</div>
      <div style={{ fontSize: 12, fontWeight: 800, marginTop: 2, fontFamily: mono ? 'DM Mono, monospace' : 'inherit' }}>{value ?? '—'}</div>
    </div>
  )
}

function RecCard({ rec, expanded, onToggle, onBuildPlan, baselineContext }) {
  const metrics = getRecommendationDisplayMetrics(rec, baselineContext)
  const urgencyLabel = {
    TODAY: 'Act today',
    THIS_SPRINT: 'This sprint',
    NEXT_SPRINT: 'Before planning',
  }[rec?.urgency] || 'This sprint'

  const tradeOff = rec?.trade_offs?.[0] || rec?.tradeoffs?.[0] || rec?.validation?.tradeoffs?.[0] || 'No major trade-off noted.'
  const title = rec?.title || rec?.recommendation_title || 'Recommendation'
  const delayGain = metrics.expectedDelayGainDays ?? rec?.expected_delay_gain_days ?? rec?.delay_gain_days ?? 0
  const benefitLine = `${delayGain} days saved`

  return (
    <div style={{ border: `1px solid ${expanded ? 'var(--teal)' : 'var(--line)'}`, borderRadius: 7, background: expanded ? 'oklch(21% .05 255)' : 'var(--panel)', padding: '9px 10px', marginBottom: 7 }}>
      <div onClick={onToggle} style={{ cursor: 'pointer' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'start' }}>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <IntentBadge intent={rec?.intent} />
              <div style={{ fontSize: 12, fontWeight: 800, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</div>
            </div>
            <div style={{ fontSize: 9, color: 'var(--muted)', marginTop: 3 }}>Primary benefit: {benefitLine}</div>
            <div style={{ fontSize: 9, color: 'var(--muted)', marginTop: 1 }}>Trade-off: {tradeOff}</div>
          </div>
          <div style={{ textAlign: 'right', minWidth: 80 }}>
            <div style={{ color: 'var(--orange)', fontSize: 8, fontWeight: 800, textTransform: 'uppercase' }}>{urgencyLabel}</div>
          </div>
        </div>
      </div>

      {expanded && (
        <div style={{ marginTop: 8, borderTop: '1px solid var(--line2)', paddingTop: 8 }}>
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: 6 }}>Current → expected project state</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 6 }}>
              <div style={{ border: '1px solid var(--line2)', borderRadius: 5, padding: '7px 8px' }}>
                <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase' }}>Delivery confidence</div>
                <div style={{ fontSize: 9, color: 'var(--muted)', marginTop: 2 }}>{metrics.baselineDeadlineProbability != null ? `${Math.round(metrics.baselineDeadlineProbability * 100)}%` : '—'}</div>
                <div style={{ fontSize: 12, color: 'var(--teal)', fontWeight: 800, marginTop: 2 }}>→ {metrics.afterDeadlineProbability != null ? `${Math.round(metrics.afterDeadlineProbability * 100)}%` : '—'}</div>
              </div>
              <div style={{ border: '1px solid var(--line2)', borderRadius: 5, padding: '7px 8px' }}>
                <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase' }}>Expected delay</div>
                <div style={{ fontSize: 9, color: 'var(--muted)', marginTop: 2 }}>{metrics.baselineDelayDays != null ? `${metrics.baselineDelayDays}d` : '—'}</div>
                <div style={{ fontSize: 12, color: 'var(--teal)', fontWeight: 800, marginTop: 2 }}>→ {metrics.expectedDelayGainDays != null ? `${metrics.expectedDelayGainDays}d` : '—'}</div>
              </div>
              <div style={{ border: '1px solid var(--line2)', borderRadius: 5, padding: '7px 8px' }}>
                <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase' }}>Risk score</div>
                <div style={{ fontSize: 9, color: 'var(--muted)', marginTop: 2 }}>{metrics.baselineRiskScore ?? '—'}</div>
                <div style={{ fontSize: 12, color: 'var(--teal)', fontWeight: 800, marginTop: 2 }}>→ {metrics.afterRiskScore ?? '—'}</div>
              </div>
            </div>
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: 6 }}>Where the delay saving comes from</div>
            <div style={{ display: 'flex', gap: 0, border: '1px solid var(--line2)', borderRadius: 5, overflow: 'hidden' }}>
              {(metrics.delayAttributionSegments || [{ source: 'Direct impact', days: rec?.expected_delay_gain_days ?? 0 }]).map((segment, index) => (
                <div key={`${segment.source}-${index}`} style={{ flex: 1, padding: '8px 9px', borderRight: index < (metrics.delayAttributionSegments?.length || 1) - 1 ? '1px solid var(--line2)' : 'none', background: 'rgba(255,255,255,.02)' }}>
                  <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase' }}>{segment.source}</div>
                  <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--teal)', marginTop: 2, fontFamily: 'DM Mono, monospace' }}>{segment.days ?? 0}d</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: 6 }}>Implementation cost</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 6 }}>
              <MetricTile label="Capacity hours" value={rec?.estimated_hours ?? rec?.actions?.reduce((sum, action) => sum + (action?.hours || 0), 0) ?? '—'} mono />
              <MetricTile label="Urgency" value={urgencyLabel} />
              <MetricTile label="Effort" value={rec?.effort_level || 'Medium'} />
            </div>
          </div>

          {rec?.validation?.why_better_than_alternatives?.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: 6 }}>Why ranked above alternatives</div>
              <ol style={{ paddingLeft: 16, margin: 0 }}>
                {rec.validation.why_better_than_alternatives.map((reason, index) => (
                  <li key={`${reason}-${index}`} style={{ fontSize: 9, color: 'var(--muted)', marginBottom: 3 }}><span style={{ color: 'var(--teal)', fontWeight: 800 }}>{index + 1}.</span> {reason}</li>
                ))}
              </ol>
            </div>
          )}

          <div style={{ marginBottom: 8, display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 6 }}>
            <div style={{ border: '1px solid var(--line2)', borderRadius: 5, padding: '7px 8px' }}>
              <div style={{ fontSize: 8, color: 'var(--yellow)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Trade-offs</div>
              <ul style={{ paddingLeft: 14, margin: '4px 0 0', color: 'var(--muted)', fontSize: 9 }}>
                {(rec?.trade_offs || rec?.tradeoffs || []).map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
              </ul>
            </div>
            <div style={{ border: '1px solid var(--line2)', borderRadius: 5, padding: '7px 8px' }}>
              <div style={{ fontSize: 8, color: 'var(--pink)', textTransform: 'uppercase', letterSpacing: '.08em' }}>Counterfactual</div>
              <div style={{ fontSize: 9, color: 'var(--muted)', marginTop: 4 }}>{metrics.counterfactualStatement || 'No counterfactual provided.'}</div>
            </div>
          </div>

          {rec?.validation?.why_selected?.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase', letterSpacing: '.12em', marginBottom: 6 }}>AI assumptions</div>
              <ul style={{ paddingLeft: 14, margin: 0 }}>
                {rec.validation.why_selected.map((item, index) => <li key={`${item}-${index}`} style={{ fontSize: 9, color: 'var(--muted)', marginBottom: 3 }}>{item}</li>)}
              </ul>
            </div>
          )}

          <button onClick={onBuildPlan} style={{ width: '100%', border: 'none', background: 'var(--teal)', color: 'var(--bg)', borderRadius: 4, padding: '8px 10px', fontWeight: 800, cursor: 'pointer', fontSize: 10 }}>
            Build recovery plan for this recommendation ↗
          </button>
        </div>
      )}
    </div>
  )
}

function AIReadingGuide() {
  return (
    <div style={{ background: 'oklch(14% .034 255)', border: '1px solid var(--line)', borderRadius: 7, padding: 11 }}>
      <div style={{ fontSize: 8, color: 'var(--orange)', fontWeight: 800, letterSpacing: '.18em', textTransform: 'uppercase' }}>AI reading guide</div>
      <div style={{ fontSize: 12, fontWeight: 800, marginTop: 4 }}>How to read these recommendations</div>
      <ul style={{ paddingLeft: 14, margin: '8px 0 0', color: 'var(--muted)', fontSize: 9, lineHeight: 1.6 }}>
        <li><strong style={{ color: 'var(--teal)' }}>Delay days</strong> show how much time might be recovered.</li>
        <li><strong style={{ color: 'var(--teal)' }}>Confidence</strong> reflects how much the model trusts the move.</li>
        <li><strong style={{ color: 'var(--teal)' }}>Trade-offs</strong> capture what might be deprioritized.</li>
        <li><strong style={{ color: 'var(--teal)' }}>If ignored</strong> captures what remains likely without action.</li>
      </ul>
      <div style={{ marginTop: 8, fontSize: 9, color: 'var(--muted)' }}>0.0 days saved can still be the right move.</div>
    </div>
  )
}

export default function RecommendationsPage({ session, onNavigate }) {
  const [recs, setRecs] = useState([])
  const [subnav, setSubnav] = useState('overview')
  const [expandedId, setExpandedId] = useState(null)
  const [baselineContext, setBaselineContext] = useState(null)

  useEffect(() => {
    const sessionId = session?.project_summary?.session_id
    if (!sessionId) return

    let mounted = true
    Promise.all([
      api.recommendations(sessionId),
      api.sessionSnapshot(sessionId),
    ])
      .then(([data, snapshot]) => {
        if (!mounted) return
        const list = Array.isArray(data?.recommendations) ? data.recommendations : []
        setRecs(list)
        if (list[0]) setExpandedId(list[0].recommendation_id || list[0].id || 0)
        setBaselineContext({
          baseline_deadline_prob: snapshot?.monte_carlo?.on_time_probability ?? null,
          baseline_delay: snapshot?.forecast?.expected_delay_days ?? null,
          baseline_risk: snapshot?.risk?.overall_risk_score ?? null,
        })
      })
      .catch(() => {
        if (!mounted) return
        setRecs([])
        setBaselineContext(null)
      })

    return () => { mounted = false }
  }, [session?.project_summary?.session_id])

  const totalDelayAtRisk = recs.reduce((sum, rec) => sum + (getRecommendationDisplayMetrics(rec).expectedDelayGainDays ?? 0), 0)
  const highestConfidence = recs.reduce((best, rec) => {
    const conf = rec?.confidence_score ?? rec?.confidence ?? 0
    if (!best || conf > best.score) return { score: conf, value: rec?.title || 'N/A' }
    return best
  }, null)

  const summaryKpis = [
    { label: 'Decisions needing action', value: recs.length || '—' },
    { label: 'Total delay at risk', value: `${totalDelayAtRisk}d` },
    { label: 'Highest-confidence move', value: highestConfidence?.value || '—' },
  ]

  return (
    <div>
      <div style={{ border: '1px solid var(--line)', borderRadius: 7, background: 'var(--panel)', padding: '10px 11px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 8, color: 'var(--orange)', fontWeight: 800, letterSpacing: '.18em', textTransform: 'uppercase' }}>Decision intelligence</div>
            <div style={{ fontSize: 14, fontWeight: 800, marginTop: 4 }}>{recs.length} decisions need a PM read this sprint</div>
            <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 3 }}>Delay days are one signal; make sure the team also considers confidence, trade-offs, and effort.</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button style={{ border: '1px solid var(--line)', background: 'var(--panel2)', color: 'var(--muted)', borderRadius: 4, padding: '6px 8px', fontSize: 9, cursor: 'pointer' }}>Refresh signals</button>
            <button style={{ border: '1px solid var(--line)', background: 'var(--panel2)', color: 'var(--muted)', borderRadius: 4, padding: '6px 8px', fontSize: 9, cursor: 'pointer' }}>Export readout</button>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 6, marginTop: 9 }}>
          {summaryKpis.map((kpi) => (
            <div key={kpi.label} style={{ border: '1px solid var(--line2)', borderRadius: 5, padding: '7px 8px' }}>
              <div style={{ fontSize: 8, color: 'var(--quiet)', textTransform: 'uppercase', letterSpacing: '.08em' }}>{kpi.label}</div>
              <div style={{ fontSize: 12, fontWeight: 800, marginTop: 2 }}>{kpi.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
        {['overview', 'log', 'signals'].map((key) => (
          <button
            key={key}
            onClick={() => setSubnav(key)}
            style={{ border: `1px solid ${subnav === key ? 'var(--teal)' : 'var(--line)'}`, background: subnav === key ? 'var(--teal)' : 'var(--panel)', color: subnav === key ? 'var(--bg)' : 'var(--muted)', borderRadius: 4, padding: '6px 8px', fontSize: 9, fontWeight: 700, cursor: 'pointer' }}
          >
            {key === 'overview' ? 'PM Overview' : key === 'log' ? 'Decision Log' : 'Signals'}
          </button>
        ))}
      </div>

      {subnav === 'overview' ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 240px', gap: 8, marginTop: 8 }}>
          <div>
            {recs.length === 0 ? (
              <div style={{ border: '1px solid var(--line)', borderRadius: 7, background: 'var(--panel)', padding: '11px 12px', color: 'var(--muted)', fontSize: 10 }}>No recommendations available yet.</div>
            ) : recs.map((rec) => (
              <RecCard
                key={rec.recommendation_id || rec.id || rec.title}
                rec={rec}
                expanded={expandedId === (rec.recommendation_id || rec.id || rec.title)}
                onToggle={() => setExpandedId(expandedId === (rec.recommendation_id || rec.id || rec.title) ? null : (rec.recommendation_id || rec.id || rec.title))}
                onBuildPlan={() => onNavigate && onNavigate('recovery-plans')}
                baselineContext={baselineContext}
              />
            ))}
          </div>
          <AIReadingGuide />
        </div>
      ) : subnav === 'log' ? (
        <div style={{ marginTop: 8, border: '1px solid var(--line)', borderRadius: 7, background: 'var(--panel)', padding: '11px 12px', color: 'var(--muted)', fontSize: 10 }}>Decisions you act on will appear here.</div>
      ) : (
        <div style={{ marginTop: 8, border: '1px solid var(--line)', borderRadius: 7, background: 'var(--panel)', padding: '11px 12px', color: 'var(--muted)', fontSize: 10 }}>Signal data will come from pm_intelligence fields.</div>
      )}
    </div>
  )
}
