import { useState, type FormEvent } from 'react'
import type { Interval, Place, PlanRequest } from '@/api/types'
import { LocationCombobox } from '@/components/LocationCombobox'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toDateTimeLocal } from '@/lib/format'

const INTERVALS: Interval[] = [10, 25, 50]
const MAX_LOAD_LB = 80_000
const WINDOW_MS = 5 * 24 * 60 * 60 * 1000 // D12

// Rounded in local time, so half-hour time zones still get :00.
function nextFullHour(): Date {
  const date = new Date()
  date.setMinutes(60, 0, 0)
  return date
}

type Props = {
  pending: boolean
  onSubmit: (request: PlanRequest) => void
}

export function PlanForm({ pending, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toDateTimeLocal(nextFullHour()))
  const [load, setLoad] = useState('')
  const [intervalMi, setIntervalMi] = useState<Interval>(25)

  const now = new Date()

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!origin || !destination) return
    onSubmit({
      origin,
      destination,
      // datetime-local values parse as local time; the API takes UTC.
      departure_at: new Date(departure).toISOString(),
      load_lb: Number(load),
      interval_mi: intervalMi,
    })
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <LocationCombobox id="origin" label="Origin" value={origin} onChange={setOrigin} />
      <LocationCombobox id="destination" label="Destination" value={destination} onChange={setDestination} />

      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Departure
        <Input
          type="datetime-local"
          required
          value={departure}
          min={toDateTimeLocal(now)}
          max={toDateTimeLocal(new Date(now.getTime() + WINDOW_MS))}
          onChange={(event) => setDeparture(event.target.value)}
        />
      </label>

      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Load (lb)
        <Input
          type="number"
          required
          min={0}
          max={MAX_LOAD_LB}
          step={1}
          inputMode="numeric"
          placeholder="e.g. 42000"
          value={load}
          onChange={(event) => setLoad(event.target.value)}
        />
      </label>

      <fieldset className="flex flex-col gap-1.5">
        <legend className="mb-1.5 text-sm font-medium">Checkpoint every</legend>
        <div className="grid grid-cols-3 gap-1">
          {INTERVALS.map((miles) => (
            <Button
              key={miles}
              type="button"
              variant={intervalMi === miles ? 'default' : 'outline'}
              aria-pressed={intervalMi === miles}
              onClick={() => setIntervalMi(miles)}
            >
              {miles} mi
            </Button>
          ))}
        </div>
      </fieldset>

      <Button type="submit" disabled={!origin || !destination || !load || pending}>
        {pending ? 'Finding route…' : 'Plan route'}
      </Button>
    </form>
  )
}
