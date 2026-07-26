import { useEffect, useState } from 'react'

const API_BASE = 'http://localhost:5000/api'

function Panel({ title, children, flex = 1 }) {
  return (
    <div className="panel" style={{ flex, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{
        padding: 'var(--space-3)', borderBottom: '1px solid var(--border-hairline)',
        fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 13,
        textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)',
      }}>
        {title}
      </div>
      <div style={{ overflowY: 'auto', flex: 1, padding: 'var(--space-2) 0' }}>
        {children}
      </div>
    </div>
  )
}

function Bar({ pct, color }) {
  return (
    <div style={{ background: 'var(--bg-primary)', borderRadius: 2, height: 5, overflow: 'hidden', marginTop: 4 }}>
      <div style={{ width: `${Math.min(100, pct)}%`, height: '100%', background: color, borderRadius: 2 }} />
    </div>
  )
}

function TrendAlertsPanel() {
  const [alerts, setAlerts] = useState([])
  useEffect(() => {
    fetch(`${API_BASE}/trend-alerts`).then((r) => r.json()).then(setAlerts).catch(() => setAlerts([]))
  }, [])

  const maxZ = Math.max(...alerts.map((a) => a.z_score), 1)

  return (
    <Panel title={`Trend Alerts (${alerts.length})`}>
      {alerts.length === 0 && (
        <div style={{ padding: 'var(--space-3)', fontSize: 12, color: 'var(--text-muted)' }}>No active alerts.</div>
      )}
      {alerts.map((a, i) => (
        <div key={i} style={{ padding: 'var(--space-2) var(--space-3)', borderBottom: '1px solid var(--border-hairline)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
            <span>{a.DistrictName} — {a.subhead}</span>
            <span className="mono" style={{ color: 'var(--accent-alert)' }}>z={a.z_score}</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {a.month}: {a.n_cases} cases (baseline {a.baseline_mean})
          </div>
          <Bar pct={(a.z_score / maxZ) * 100} color="var(--accent-alert)" />
        </div>
      ))}
    </Panel>
  )
}

function RiskScoresPanel() {
  const [scores, setScores] = useState([])
  useEffect(() => {
    fetch(`${API_BASE}/risk-scores`).then((r) => r.json()).then(setScores).catch(() => setScores([]))
  }, [])

  return (
    <Panel title={`High-Risk Open Cases (${scores.filter((s) => s.risk_score > 0.6).length})`}>
      {scores.slice(0, 25).map((s) => (
        <div key={s.CaseMasterID} style={{ padding: 'var(--space-2) var(--space-3)', borderBottom: '1px solid var(--border-hairline)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
            <span className="mono">{s.CrimeNo}</span>
            <span className="mono" style={{ color: s.risk_score > 0.6 ? 'var(--accent-alert)' : 'var(--text-muted)' }}>
              {(s.risk_score * 100).toFixed(0)}%
            </span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.DistrictName} — {s.subhead}</div>
          <Bar pct={s.risk_score * 100} color={s.risk_score > 0.6 ? 'var(--accent-alert)' : 'var(--accent-resolved)'} />
        </div>
      ))}
    </Panel>
  )
}

function SocioEconomicPanel() {
  const [districts, setDistricts] = useState([])
  useEffect(() => {
    fetch(`${API_BASE}/districts`).then((r) => r.json()).then(setDistricts).catch(() => setDistricts([]))
  }, [])

  const withRates = districts.filter((d) => d.property_crime_rate_per_100k != null)
    .sort((a, b) => b.property_crime_rate_per_100k - a.property_crime_rate_per_100k)
    .slice(0, 12)
  const maxRate = Math.max(...withRates.map((d) => d.property_crime_rate_per_100k), 1)

  return (
    <Panel title="Property Crime Rate vs. Unemployment (Top 12 Districts)">
      <div style={{ padding: '0 var(--space-3) var(--space-2)', fontSize: 10.5, color: 'var(--text-muted)' }}>
        r = 0.92 (unemployment ↔ property crime) — see PPT for methodology
      </div>
      {withRates.map((d) => (
        <div key={d.DistrictID} style={{ padding: 'var(--space-2) var(--space-3)', borderBottom: '1px solid var(--border-hairline)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
            <span>{d.DistrictName}</span>
            <span className="mono" style={{ color: 'var(--text-muted)' }}>
              {d.property_crime_rate_per_100k?.toFixed(1)} / 100k · {d.unemployment_rate}% unemp.
            </span>
          </div>
          <Bar pct={(d.property_crime_rate_per_100k / maxRate) * 100} color="var(--accent-resolved)" />
        </div>
      ))}
    </Panel>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/trend-alerts`).then((r) => r.json()).catch(() => []),
      fetch(`${API_BASE}/risk-scores`).then((r) => r.json()).catch(() => []),
    ]).then(([alerts, scores]) => {
      setSummary({
        alerts: alerts.length,
        highRisk: scores.filter((s) => s.risk_score > 0.6).length,
        topAlert: alerts[0],
      })
    })
  }, [])

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {summary && (
        <div style={{
          padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--border-hairline)',
          fontSize: 13, color: 'var(--text-primary)', background: 'var(--bg-panel)',
        }}>
          <span style={{ color: 'var(--accent-alert)', fontWeight: 600 }}>{summary.alerts} active red-zone alerts</span>
          {summary.topAlert && (
            <span style={{ color: 'var(--text-muted)' }}>
              {' '}— highest severity: {summary.topAlert.DistrictName} ({summary.topAlert.subhead}, z={summary.topAlert.z_score})
            </span>
          )}
          <span style={{ color: 'var(--text-muted)' }}> · </span>
          <span style={{ color: 'var(--accent-alert)', fontWeight: 600 }}>{summary.highRisk} open cases</span>
          <span style={{ color: 'var(--text-muted)' }}> flagged high-risk of going undetected</span>
        </div>
      )}
      <div style={{ flex: 1, display: 'flex', gap: 1, overflow: 'hidden', background: 'var(--border-hairline)' }}>
        <TrendAlertsPanel />
        <RiskScoresPanel />
        <SocioEconomicPanel />
      </div>
    </div>
  )
}