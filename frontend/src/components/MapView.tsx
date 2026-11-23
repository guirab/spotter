import { LngLatBounds, setWorkerUrl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useMemo, useRef, useState } from 'react'
import Map, { Layer, Popup, Source, type MapLayerMouseEvent, type MapRef } from 'react-map-gl/maplibre'
import type { Checkpoint, Route } from '@/api/types'
import { formatDateTime, formatMiles } from '@/lib/format'

// MapLibre 6 looks for its worker next to its own module, which bundling breaks.
setWorkerUrl(workerUrl)

const MAP_STYLE ='https://tiles.openfreemap.org/styles/positron'
const CONTIGUOUS_US = { longitude: -98.5, latitude: 39.5, zoom: 3.3 }
const CHECKPOINT_LAYER = 'checkpoints'

export function MapView({ route }: { route?: Route }) {
  const mapRef = useRef<MapRef>(null)
  const [selected, setSelected] = useState<Checkpoint | null>(null)
  const [cursor, setCursor] = useState('')
  // A checkpoint from an earlier plan closes its popup.
  const openCheckpoint = selected && route?.checkpoints.includes(selected) ? selected : null

  const routeLine = useMemo(
    () =>
      route && {
        type: 'Feature' as const,
        properties: {},
        geometry: { type: 'LineString' as const, coordinates: route.geometry },
      },
    [route],
  )

  const checkpointPoints = useMemo(
    () =>
      route && {
        type: 'FeatureCollection' as const,
        features: route.checkpoints.map((c, index) => ({
          type: 'Feature' as const,
          properties: { index },
          geometry: { type: 'Point' as const, coordinates: [c.lon, c.lat] },
        })),
      },
    [route],
  )

  function selectCheckpoint(event: MapLayerMouseEvent) {
    const index = event.features?.[0]?.properties.index
    setSelected(typeof index === 'number' && route ? route.checkpoints[index] : null)
  }

  useEffect(() => {
    if (!route?.geometry.length) return
    const [first] = route.geometry
    const bounds = route.geometry.reduce((b, point) => b.extend(point), new LngLatBounds(first, first))
    mapRef.current?.fitBounds(bounds, { padding: 48, duration: 800 })
  }, [route])

  return (
    <Map
      ref={mapRef}
      initialViewState={CONTIGUOUS_US}
      mapStyle={MAP_STYLE}
      style={{ width: '100%', height: '100%' }}
      interactiveLayerIds={[CHECKPOINT_LAYER]}
      cursor={cursor}
      onClick={selectCheckpoint}
      onMouseEnter={() => setCursor('pointer')}
      onMouseLeave={() => setCursor('')}
    >
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
      {checkpointPoints && (
        <Source id="checkpoints" type="geojson" data={checkpointPoints}>
          <Layer
            id={CHECKPOINT_LAYER}
            type="circle"
            paint={{
              'circle-radius': 5,
              'circle-color': '#ffffff',
              'circle-stroke-color': '#1e3a8a',
              'circle-stroke-width': 2,
            }}
          />
        </Source>
      )}
      {openCheckpoint && (
        // The map's own click handler moves or closes the popup; Popup's closeOnClick would race it.
        <Popup
          longitude={openCheckpoint.lon}
          latitude={openCheckpoint.lat}
          offset={10}
          closeOnClick={false}
          onClose={() => setSelected(null)}
        >
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted-foreground">Mile</dt>
            <dd>{formatMiles(openCheckpoint.mile)}</dd>
            <dt className="text-muted-foreground">ETA</dt>
            <dd>{formatDateTime(openCheckpoint.eta)}</dd>
          </dl>
        </Popup>
      )}
    </Map>
  )
}
