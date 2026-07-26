import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Marker, Tooltip } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './tokens.css'
import NetworkView from './NetworkView'
import Dashboard from './Dashboard'
import HeatmapLayer from './HeatmapLayer'

const API_BASE = 'http://localhost:5000/api'
const KARNATAKA_CENTER = [15.3, 75.7]

const TIME_PRESETS = [
  { key: 'all', label: 'All Day', range: [0, 23] },
  { key: 'night', label: 'Night (0–5)', range: [0, 5] },
  { key: 'morning', label: 'Morning (6–11)', range: [6, 11] },
  { key: 'afternoon', label: 'Afternoon (12–17)', range: [12, 17] },
  { key: 'evening', label: 'Evening (18–23)', range: [18, 23] },
]

function StatStrip({ stats }) {
  if (!stats) return null
  const items = [
    { label: 'Total Cases', value: stats.total_cases },
    { label: 'Resolved Identities', value: stats.resolved_persons },
    { label: 'Repeat Offenders', value: stats.repeat_offenders },
    { label: 'Cross-Jurisdiction', value: stats.cross_jurisdiction_offenders },
    { label: 'Anomalies Flagged', value: stats.anomalous_cases_flagged },
  ]
  return (
    <div style={{ display: 'flex', gap: 'var(--space-5)', padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--border-hairline)', background: 'var(--bg-panel)' }}>
      {items.map((it) => (
        <div key={it.label}>
          <div className="mono" style={{ fontSize: 22, fontWeight: 600 }}>{it.value?.toLocaleString()}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{it.label}</div>
        </div>
      ))}
    </div>
  )
}

function DistrictList({ districts, selected, onSelect }) {
  return (
    <div className="panel" style={{ width: 260, overflowY: 'auto', flexShrink: 0 }}>
      <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--border-hairline)', fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
        Districts
      </div>
      {districts.sort((a, b) => (b.total_cases || 0) - (a.total_cases || 0)).map((d) => (
        <div key={d.DistrictID} onClick={() => onSelect(d.DistrictID === selected ? null : d.DistrictID)}
          style={{
            padding: 'var(--space-2) var(--space-3)', cursor: 'pointer',
            background: selected === d.DistrictID ? 'var(--bg-panel-hover)' : 'transparent',
            borderLeft: selected === d.DistrictID ? '3px solid var(--accent-alert)' : '3px solid transparent',
            borderBottom: '1px solid var(--border-hairline)',
          }}>
          <div style={{ fontSize: 13 }}>{d.DistrictName}</div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{d.total_cases?.toLocaleString() || 0} cases</div>
        </div>
      ))}
    </div>
  )
}

function StationList({ districtName, stations, selectedStation, onSelectStation, onBack }) {
  return (
    <div className="panel" style={{ width: 260, overflowY: 'auto', flexShrink: 0 }}>
      <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--border-hairline)' }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--accent-alert)', fontSize: 11, cursor: 'pointer', padding: 0, marginBottom: 6, fontFamily: 'var(--font-body)' }}>
          ← Back to Districts
        </button>
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
          Stations — {districtName}
        </div>
      </div>
      <div onClick={() => onSelectStation(null)}
        style={{ padding: 'var(--space-2) var(--space-3)', cursor: 'pointer', fontSize: 12.5,
          background: !selectedStation ? 'var(--bg-panel-hover)' : 'transparent',
          borderLeft: !selectedStation ? '3px solid var(--accent-alert)' : '3px solid transparent',
          borderBottom: '1px solid var(--border-hairline)' }}>
        All Stations
      </div>
      {stations.map((s) => (
        <div key={s.UnitID} onClick={() => onSelectStation(s.UnitID === selectedStation ? null : s.UnitID)}
          style={{
            padding: 'var(--space-2) var(--space-3)', cursor: 'pointer',
            background: selectedStation === s.UnitID ? 'var(--bg-panel-hover)' : 'transparent',
            borderLeft: selectedStation === s.UnitID ? '3px solid var(--accent-alert)' : '3px solid transparent',
            borderBottom: '1px solid var(--border-hairline)',
          }}>
          <div style={{ fontSize: 12.5 }}>{s.UnitName}</div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{Math.round(s.case_count)} cases</div>
        </div>
      ))}
    </div>
  )
}

function pulseIcon() {
  return L.divIcon({ className: '', html: '<div class="pulse-ring"></div>', iconSize: [20, 20], iconAnchor: [10, 10] })
}
function gravityColor(g) { return g === 1 ? '#C4432B' : '#4A7DBD' }

function ViewTabs({ view, setView }) {
  const tabs = [{ key: 'map', label: 'Map' }, { key: 'network', label: 'Network' }, { key: 'dashboard', label: 'Intelligence' }]
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {tabs.map((t) => (
        <button key={t.key} onClick={() => setView(t.key)}
          style={{
            padding: '6px 14px', fontSize: 12, fontFamily: 'var(--font-display)', fontWeight: 600,
            textTransform: 'uppercase', letterSpacing: '0.05em', border: '1px solid var(--border-hairline)',
            borderRadius: 3, cursor: 'pointer',
            background: view === t.key ? 'var(--accent-alert)' : 'transparent',
            color: view === t.key ? '#fff' : 'var(--text-muted)',
          }}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

function MapControls({ heatmapMode, setHeatmapMode, timeKey, setTimeKey }) {
  return (
    <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 1000, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div className="panel" style={{ display: 'flex', padding: 3, gap: 2 }}>
        {['points', 'heatmap'].map((m) => (
          <button key={m} onClick={() => setHeatmapMode(m === 'heatmap')}
            style={{
              padding: '5px 10px', fontSize: 11, fontFamily: 'var(--font-display)', fontWeight: 600,
              textTransform: 'uppercase', border: 'none', borderRadius: 3, cursor: 'pointer',
              background: (m === 'heatmap') === heatmapMode ? 'var(--accent-alert)' : 'transparent',
              color: (m === 'heatmap') === heatmapMode ? '#fff' : 'var(--text-muted)',
            }}>
            {m}
          </button>
        ))}
      </div>
      <div className="panel" style={{ padding: 6 }}>
        {TIME_PRESETS.map((t) => (
          <div key={t.key} onClick={() => setTimeKey(t.key)}
            style={{
              padding: '4px 10px', fontSize: 11, cursor: 'pointer', borderRadius: 3,
              background: timeKey === t.key ? 'var(--bg-panel-hover)' : 'transparent',
              color: timeKey === t.key ? 'var(--accent-alert)' : 'var(--text-muted)',
            }}>
            {t.label}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [stats, setStats] = useState(null)
  const [districts, setDistricts] = useState([])
  const [cases, setCases] = useState([])
  const [alerts, setAlerts] = useState([])
  const [centroids, setCentroids] = useState([])
  const [selectedDistrict, setSelectedDistrict] = useState(null)
  const [stations, setStations] = useState([])
  const [selectedStation, setSelectedStation] = useState(null)
  const [view, setView] = useState('map')
  const [heatmapMode, setHeatmapMode] = useState(false)
  const [timeKey, setTimeKey] = useState('all')

  useEffect(() => {
    fetch(`${API_BASE}/stats`).then((r) => r.json()).then(setStats)
    fetch(`${API_BASE}/districts`).then((r) => r.json()).then(setDistricts)
    fetch(`${API_BASE}/trend-alerts`).then((r) => r.json()).then(setAlerts).catch(() => setAlerts([]))
    fetch(`${API_BASE}/district-centroids`).then((r) => r.json()).then(setCentroids).catch(() => setCentroids([]))
  }, [])

  useEffect(() => {
    const url = selectedDistrict ? `${API_BASE}/cases?district_id=${selectedDistrict}` : `${API_BASE}/cases`
    fetch(url).then((r) => r.json()).then(setCases)
  }, [selectedDistrict])

  useEffect(() => {
    if (!selectedDistrict) { setStations([]); setSelectedStation(null); return }
    fetch(`${API_BASE}/stations?district_id=${selectedDistrict}`).then((r) => r.json()).then(setStations).catch(() => setStations([]))
    setSelectedStation(null)
  }, [selectedDistrict])

  const alertDistrictNames = new Set(alerts.map((a) => a.DistrictName))
  const alertCentroids = centroids.filter((c) => alertDistrictNames.has(c.DistrictName))

  const timeRange = TIME_PRESETS.find((t) => t.key === timeKey).range
  const visibleCases = cases
    .filter((c) => c.hour >= timeRange[0] && c.hour <= timeRange[1])
    .filter((c) => !selectedStation || c.PoliceStationID === selectedStation)

  const selectedDistrictName = districts.find((d) => d.DistrictID === selectedDistrict)?.DistrictName

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', fontFamily: 'var(--font-body)' }}>
      <div style={{ padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--border-hairline)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600 }}>CRIMEGRAPH</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Karnataka Crime Intelligence Platform</div>
        </div>
        <ViewTabs view={view} setView={setView} />
      </div>

      <StatStrip stats={stats} />

      {view === 'map' ? (
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {selectedDistrict ? (
            <StationList
              districtName={selectedDistrictName}
              stations={stations}
              selectedStation={selectedStation}
              onSelectStation={setSelectedStation}
              onBack={() => setSelectedDistrict(null)}
            />
          ) : (
            <DistrictList districts={districts} selected={selectedDistrict} onSelect={setSelectedDistrict} />
          )}

          <div style={{ flex: 1, position: 'relative' }}>
            <MapControls heatmapMode={heatmapMode} setHeatmapMode={setHeatmapMode} timeKey={timeKey} setTimeKey={setTimeKey} />
            <MapContainer center={KARNATAKA_CENTER} zoom={7} style={{ height: '100%', width: '100%', background: 'var(--bg-primary)' }}>
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution='&copy; OpenStreetMap &copy; CARTO' />

              {heatmapMode ? (
                <HeatmapLayer points={visibleCases} />
              ) : (
                visibleCases.map((c) => (
                  <CircleMarker key={c.CaseMasterID} center={[c.latitude, c.longitude]} radius={5}
                    pathOptions={{ color: gravityColor(c.GravityOffenceID), fillOpacity: 0.7, weight: 1 }}>
                    <Tooltip><div className="mono">{c.CrimeNo}</div><div>{c.subhead}</div></Tooltip>
                  </CircleMarker>
                ))
              )}

              {alertCentroids.map((c) => (
                <Marker key={c.DistrictName} position={[c.avg_lat, c.avg_lon]} icon={pulseIcon()}>
                  <Tooltip>Trend alert: {c.DistrictName}</Tooltip>
                </Marker>
              ))}
            </MapContainer>
          </div>
        </div>
      ) : view === 'network' ? (
        <NetworkView />
      ) : (
        <Dashboard />
      )}
    </div>
  )
}