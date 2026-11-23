import { LngLatBounds, setWorkerUrl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useMemo, useRef } from 'react'
import Map, { Layer, Source, type MapRef } from 'react-map-gl/maplibre'
import type { Route } from '@/api/types'

// MapLibre 6 looks for its worker next to its own module, which bundling breaks.
setWorkerUrl(workerUrl)

const MAP_STYLE ='https://tiles.openfreemap.org/styles/positron'
const CONTIGUOUS_US = { longitude: -98.5, latitude: 39.5, zoom: 3.3 }

export function MapView({ route }: { route?: Route }) {
  const mapRef = useRef<MapRef>(null)

  const routeLine = useMemo(
    () =>
      route && {
        type: 'Feature' as const,
        properties: {},
        geometry: { type: 'LineString' as const, coordinates: route.geometry },
      },
    [route],
  )

  useEffect(() => {
    if (!route?.geometry.length) return
    const [first] = route.geometry
    const bounds = route.geometry.reduce((b, point) => b.extend(point), new LngLatBounds(first, first))
    mapRef.current?.fitBounds(bounds, { padding: 48, duration: 800 })
  }, [route])

  return (
    <Map ref={mapRef} initialViewState={CONTIGUOUS_US} mapStyle={MAP_STYLE} style={{ width: '100%', height: '100%' }}>
      {routeLine && (
        <Source id="route" type="geojson" data={routeLine}>
          <Layer
            id="route-line"
            type="line"
            layout={{ 'line-join': 'round', 'line-cap': 'round' }}
            paint={{ 'line-color': '#1e3a8a', 'line-width': 5 }}
          />
        </Source>
      )}
    </Map>
  )
}
