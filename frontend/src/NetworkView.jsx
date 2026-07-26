import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const API_BASE = 'http://localhost:5000/api'

const COMMUNITY_COLORS = [
  '#C4432B', '#4A7DBD', '#2E7D5B', '#B8860B', '#8B5CF6',
  '#DB6E6E', '#4FA3A3', '#C98A3C', '#7A9E5E', '#A75D9E',
]
function communityColor(id) {
  return COMMUNITY_COLORS[id % COMMUNITY_COLORS.length]
}

const NODE_COLORS = { suspect: '#4A7DBD', victim: '#B8860B', location: '#5B6478' }
const NODE_SHAPES = { suspect: d3.symbolCircle, victim: d3.symbolTriangle, location: d3.symbolSquare }

function SearchPanel({ offenders, onSelect, selectedId }) {
  const [query, setQuery] = useState('')
  const filtered = offenders.filter((o) =>
    String(o.ResolvedPersonID).includes(query) ||
    (o.dominant_crime || '').toLowerCase().includes(query.toLowerCase())
  )
  return (
    <div className="panel" style={{ width: 300, overflowY: 'auto', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--border-hairline)' }}>
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 8 }}>
          Repeat Offenders
        </div>
        <input
          value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by ID or crime type..."
          style={{ width: '100%', padding: '6px 8px', background: 'var(--bg-primary)', border: '1px solid var(--border-hairline)', borderRadius: 3, color: 'var(--text-primary)', fontSize: 12, fontFamily: 'var(--font-body)' }}
        />
      </div>
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {filtered.map((o) => (
          <div key={o.ResolvedPersonID} onClick={() => onSelect(o.ResolvedPersonID)}
            style={{
              padding: 'var(--space-2) var(--space-3)', cursor: 'pointer',
              background: selectedId === o.ResolvedPersonID ? 'var(--bg-panel-hover)' : 'transparent',
              borderLeft: selectedId === o.ResolvedPersonID ? '3px solid var(--accent-alert)' : '3px solid transparent',
              borderBottom: '1px solid var(--border-hairline)',
            }}>
            <div className="mono" style={{ fontSize: 12 }}>Person #{o.ResolvedPersonID}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {o.n_cases} cases · {o.n_districts} district{o.n_districts !== 1 ? 's' : ''} · {o.dominant_crime}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function DetailPanel({ person, offenders }) {
  if (!person) {
    return (
      <div className="panel" style={{ width: 280, padding: 'var(--space-3)', flexShrink: 0 }}>
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Select a repeat offender to explore their network.</div>
      </div>
    )
  }
  const profile = offenders.find((o) => o.ResolvedPersonID === person)
  return (
    <div className="panel" style={{ width: 280, padding: 'var(--space-3)', flexShrink: 0, overflowY: 'auto' }}>
      <div className="mono" style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Person #{person}</div>
      {profile ? (
        <>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
            {profile.n_cases} FIRs across {profile.n_districts} district{profile.n_districts !== 1 ? 's' : ''}
            {profile.cross_jurisdiction && <span style={{ color: 'var(--accent-alert)' }}> — cross-jurisdiction</span>}
          </div>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 4 }}>Dominant Crime</div>
          <div style={{ fontSize: 13, marginBottom: 12 }}>{profile.dominant_crime}</div>
          {profile.dominant_mo_phrase && profile.mo_consistency >= 0.5 && (
            <>
              <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 4 }}>
                MO Signature ({Math.round(profile.mo_consistency * 100)}% consistency)
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.4 }}>{profile.dominant_mo_phrase}</div>
            </>
          )}
          {profile.dominant_mo_phrase && profile.mo_consistency < 0.5 && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No consistent MO pattern detected across this person's cases (below 50% threshold).
            </div>
          )}
        </>
      ) : (
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Connected to the selected person (not itself a filtered repeat offender).</div>
      )}
    </div>
  )
}

function Legend() {
  const items = [
    { shape: 'circle', color: NODE_COLORS.suspect, label: 'Suspect (co-accused)' },
    { shape: 'circle', color: '#C4432B', label: 'Selected person' },
    { shape: 'triangle', color: NODE_COLORS.victim, label: 'Victim' },
    { shape: 'square', color: NODE_COLORS.location, label: 'Location (station)' },
  ]
  return (
    <div style={{
      position: 'absolute', bottom: 16, left: 16, background: 'var(--bg-panel)',
      border: '1px solid var(--border-hairline)', borderRadius: 4, padding: '10px 14px', fontSize: 11.5,
    }}>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: 8, fontSize: 10.5 }}>
        Legend
      </div>
      {items.map((it, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <svg width="14" height="14">
            {it.shape === 'circle' && <circle cx="7" cy="7" r="6" fill={it.color} />}
            {it.shape === 'triangle' && <polygon points="7,1 13,13 1,13" fill={it.color} />}
            {it.shape === 'square' && <rect x="1" y="1" width="12" height="12" fill={it.color} />}
          </svg>
          <span style={{ color: 'var(--text-primary)' }}>{it.label}</span>
        </div>
      ))}
      <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--border-hairline)', color: 'var(--text-muted)', fontSize: 10.5 }}>
        Line thickness = shared cases. Click any node to recenter.
      </div>
    </div>
  )
}

export default function NetworkView() {
  const svgRef = useRef(null)
  const [offenders, setOffenders] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [graphData, setGraphData] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/top-offenders`).then((r) => r.json()).then(setOffenders)
  }, [])

  useEffect(() => {
    if (!selectedId) return
    fetch(`${API_BASE}/network/person/${selectedId}/full`).then((r) => r.json()).then(setGraphData)
  }, [selectedId])

  useEffect(() => {
    if (!graphData || !svgRef.current) return

    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const nodes = graphData.nodes.map((d) => ({ ...d }))
    const links = graphData.edges.map((d) => ({ ...d }))

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(70).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-280))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(20))

    const link = svg.append('g')
      .selectAll('line').data(links).join('line')
      .attr('stroke', (d) => d.edge_type === 'victim' ? '#B8860B' : d.edge_type === 'location' ? '#5B6478' : '#2A3245')
      .attr('stroke-opacity', (d) => d.edge_type ? 0.5 : 1)
      .attr('stroke-width', (d) => Math.min(4, 1 + (d.weight || 1)))

    const node = svg.append('g')
      .selectAll('path').data(nodes).join('path')
      .attr('d', (d) => {
        const isCenter = d.id === graphData.center_id
        const size = isCenter ? 260 : d.node_type === 'suspect' ? 60 + Math.min((d.n_cases || 1), 10) * 12 : 90
        return d3.symbol().type(NODE_SHAPES[d.node_type] || d3.symbolCircle).size(size)()
      })
      .attr('fill', (d) => d.id === graphData.center_id ? '#C4432B' : (d.node_type === 'suspect' ? communityColor(d.community) : NODE_COLORS[d.node_type]))
      .attr('stroke', '#0D1321')
      .attr('stroke-width', 1.5)
      .style('cursor', (d) => d.node_type === 'suspect' ? 'pointer' : 'default')
      .on('click', (_, d) => { if (d.node_type === 'suspect') setSelectedId(d.id) })
      .call(
        d3.drag()
          .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
          .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
      )

    const label = svg.append('g')
      .selectAll('text').data(nodes).join('text')
      .text((d) => d.node_type === 'suspect' ? `#${d.id}` : (d.label ? d.label.split(' ').slice(0, 2).join(' ') : ''))
      .attr('font-size', 9).attr('font-family', 'IBM Plex Mono, monospace')
      .attr('fill', '#8B93A7').attr('text-anchor', 'middle').attr('dy', -14)

    simulation.on('tick', () => {
      link.attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y).attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y)
      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
      label.attr('x', (d) => d.x).attr('y', (d) => d.y)
    })

    return () => simulation.stop()
  }, [graphData])

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
      <SearchPanel offenders={offenders} onSelect={setSelectedId} selectedId={selectedId} />
      <div style={{ flex: 1, position: 'relative', background: 'var(--bg-primary)' }}>
        <svg ref={svgRef} width="100%" height="100%" />
        {!graphData && (
          <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--text-muted)', fontSize: 13 }}>
            Select a repeat offender to view their network of suspects, victims, and locations
          </div>
        )}
        {graphData && <Legend />}
      </div>
      <DetailPanel person={selectedId} offenders={offenders} />
    </div>
  )
}