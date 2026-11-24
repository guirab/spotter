import { LoaderCircle } from 'lucide-react'
import { useState, type FormEvent, type Ref } from 'react'
import type { Interval, Place, PlanErrors, PlanRequest } from '@/api/types'
import { FieldError } from '@/components/FieldError'
import { LocationCombobox } from '@/components/LocationCombobox'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { nextFullHour, toDateTimeLocal } from '@/lib/format'

const INTERVALS: Interval[] = [10, 25, 50]
const MAX_LOAD_LB = 80_000
const WINDOW_MS = 5 * 24 * 60 * 60 * 1000 // D12

type Props = {
  ref?: Ref<HTMLFormElement>
  initial?: PlanRequest
  pending: boolean
  errors: PlanErrors
  onSubmit: (request: PlanRequest) => void
}

export function PlanForm({ ref, initial, pending, errors, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(initial?.origin ?? null)
  const [destination, setDestination] = useState<Place | null>(initial?.destination ?? null)
  const [departure, setDeparture] = useState(() =>
    toDateTimeLocal(initial ? new Date(initial.departure_at) : nextFullHour()),
  )
  const [load, setLoad] = useState(initial ? String(initial.load_lb) : '')
  const [intervalMi, setIntervalMi] = useState<Interval>(initial?.interval_mi ?? 25)

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
    <form ref={ref} onSubmit={submit} className="flex flex-col gap-3">
      <LocationCombobox id="origin" label="Origin" value={origin} error={errors.origin} onChange={setOrigin} />
      <LocationCombobox
        id="destination"
        label="Destination"
        value={destination}
        error={errors.destination}
        onChange={setDestination}
      />

      <div className="flex flex-col gap-1.5">
        <label htmlFor="departure" className="text-sm font-medium">
          Departure
        </label>
        <Input
          id="departure"
          type="datetime-local"
          required
          value={departure}
          min={toDateTimeLocal(now)}
          max={toDateTimeLocal(new Date(now.getTime() + WINDOW_MS))}
          aria-invalid={!!errors.departure_at}
          aria-describedby={errors.departure_at && 'departure-error'}
          onChange={(event) => setDeparture(event.target.value)}
        />
        <FieldError id="departure-error" message={errors.departure_at} />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="load" className="text-sm font-medium">
          Load (lb)
        </label>
        <Input
          id="load"
          type="number"
          required
          min={0}
          max={MAX_LOAD_LB}
          step={1}
          inputMode="numeric"
          placeholder="e.g. 42000"
          value={load}
          aria-invalid={!!errors.load_lb}
          aria-describedby={errors.load_lb && 'load-error'}
          onChange={(event) => setLoad(event.target.value)}
        />
        <FieldError id="load-error" message={errors.load_lb} />
      </div>

      <fieldset className="flex flex-col gap-1.5" aria-describedby={errors.interval_mi && 'interval-error'}>
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
        <FieldError id="interval-error" message={errors.interval_mi} />
      </fieldset>

      <Button type="submit" disabled={!origin || !destination || !load || pending}>
        {pending && <LoaderCircle aria-hidden className="animate-spin" />}
        {pending ? 'Planning…' : 'Plan route'}
      </Button>
    </form>
  )
}
