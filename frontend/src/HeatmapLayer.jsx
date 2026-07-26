import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet.heat'

export default function HeatmapLayer({ points }) {
  const map = useMap()

  useEffect(() => {
    if (!points || points.length === 0) return
    const heatPoints = points.map((p) => [p.latitude, p.longitude, 0.6])
    const heatLayer = L.heatLayer(heatPoints, { radius: 22, blur: 18, maxZoom: 12 })
    heatLayer.addTo(map)
    return () => map.removeLayer(heatLayer)
  }, [points, map])

  return null
}