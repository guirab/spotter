import { LngLatBounds, setWorkerUrl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useMemo, useRef, useState } from 'react'
import Map, { Layer, Popup, Source, type MapLayerMouseEvent, type MapRef } from 'react-map-gl/maplibre'
import type { Checkpoint, Route } from '@/api/types'
import { formatDateTime, formatMiles } from '@/lib/format'
import { RISK_LEVELS } from '@/lib/risk'

// MapLibre 6 looks for its worker next to its own module, which bundling breaks.
setWorkerUrl(workerUrl)

const MAP_STYLE ='https://tiles.openfreemap.org/styles/positron'
const CONTIGUOUS_US = { longitude: -98.5, latitude: 39.5, zoom: 3.3 }
const CHECKPOINT_LAYER = 'checkpoints'
const ROUTE_HIT_LAYER = 'routes-hit' // invisible and wider than the lines, so they are easy to click
const SELECTED_COLOR = '#1e3a8a'
const OTHER_COLOR = '#9ca3af'

type Props = { routes?: Route[]; selectedId?: string; onSelectRoute: (id: string) => void }

export function MapView({ routes, selectedId, onSelectRoute }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [selected, setSelected] = useState<Checkpoint | null>(null)
  const [cursor, setCursor] = useState('')
  const route = routes?.find((r) => r.id === selectedId)
  // A checkpoint from an earlier plan or another route closes its popup.
  const openCheckpoint = selected && route?.checkpoints.includes(selected) ? selected : null

  // Built once per plan; selection only changes the layer filters, so the lines are never re-uploaded.
  const routeLines = useMemo(
    () =>
      routes && {
        type: 'FeatureCollection' as const,
        features: routes.map((r) => ({
          type: 'Feature' as const,
          properties: { id: r.id },
          geometry: { type: 'LineString' as const, coordinates: r.geometry },
        })),
      },
    [routes],
  )

  const checkpointPoints = useMemo(
    () =>
      route && {
        type: 'FeatureCollection' as const,
        features: route.checkpoints.map((c, index) => ({
          type: 'Feature' as const,
          properties: { index, color: RISK_LEVELS[c.level].color },
          geometry: { type: 'Point' as const, coordinates: [c.lon, c.lat] },
        })),
      },
    [route],
  )

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0] // the topmost: checkpoints are drawn above the lines
    if (feature?.layer.id !== CHECKPOINT_LAYER) {
      setSelected(null)
      // Where routes share road, the lines overlap: a click there keeps the selected one.
      const ids = event.features?.map((f) => f.properties.id) ?? []
      if (ids.length && !ids.includes(selectedId)) onSelectRoute(ids[0])
      return
    }
    const index = feature.properties.index
    setSelected(typeof index === 'number' && route ? route.checkpoints[index] : null)
  }

  useEffect(() => {
    const points = routes?.flatMap((r) => r.geometry)
    if (!points?.length) return
    const [first] = points
    const bounds = points.reduce((b, point) => b.extend(point), new LngLatBounds(first, first))
    mapRef.current?.fitBounds(bounds, { padding: 48, duration: 800 })
  }, [routes])

  return (
    <Map
      ref={mapRef}
      initialViewState={CONTIGUOUS_US}
      mapStyle={MAP_STYLE}
      style={{ width: '100%', height: '100%' }}
      interactiveLayerIds={[ROUTE_HIT_LAYER, CHECKPOINT_LAYER]}
      cursor={cursor}
      onClick={handleClick}
      onMouseEnter={() => setCursor('pointer')}
      onMouseLeave={() => setCursor('')}
    >
      {routeLines && (
        <Source id="routes" type="geojson" data={routeLines}>
          <Layer id={ROUTE_HIT_LAYER} type="line" paint={{ 'line-color': '#000000', 'line-opacity': 0, 'line-width': 16 }} />
          <Layer
            id="routes-other"
            type="line"
            filter={['!=', ['get', 'id'], selectedId ?? '']}
            layout={{ 'line-join': 'round', 'line-cap': 'round' }}
            paint={{ 'line-color': OTHER_COLOR, 'line-width': 4 }}
          />
          <Layer
            id="routes-selected"
            type="line"
            filter={['==', ['get', 'id'], selectedId ?? '']}
            layout={{ 'line-join': 'round', 'line-cap': 'round' }}
            paint={{ 'line-color': SELECTED_COLOR, 'line-width': 6 }}
          />
        </Source>
      )}
      {checkpointPoints && (
        <Source id="checkpoints" type="geojson" data={checkpointPoints}>
          <Layer
            id={CHECKPOINT_LAYER}
            type="circle"
            paint={{
              'circle-radius': 6,
              'circle-color': ['get', 'color'],
              'circle-stroke-color': '#ffffff',
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
            <dt className="text-muted-foreground">Risk</dt>
            <dd className="flex items-center gap-1.5 font-medium">
              <span
                aria-hidden
                className="size-2.5 rounded-full"
                style={{ backgroundColor: RISK_LEVELS[openCheckpoint.level].color }}
              />
              {RISK_LEVELS[openCheckpoint.level].label}
            </dd>
            <dt className="text-muted-foreground">Wind</dt>
            <dd>
              {openCheckpoint.weather.wind_mph} mph, gusts {openCheckpoint.weather.gust_mph} mph
            </dd>
            <dt className="text-muted-foreground">Rain</dt>
            <dd>{openCheckpoint.weather.rain_in_hr} in/h</dd>
            <dt className="text-muted-foreground">Snow</dt>
            <dd>{openCheckpoint.weather.snow_in_hr} in/h</dd>
          </dl>
          {openCheckpoint.reasons.length > 0 && (
            <ul className="mt-2 list-disc pl-4 text-xs text-muted-foreground">
              {openCheckpoint.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
        </Popup>
      )}
    </Map>
  )
}
