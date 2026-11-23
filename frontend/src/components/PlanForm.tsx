import { useState, type FormEvent } from 'react'
import type { Place, PlanRequest } from '@/api/types'
import { LocationCombobox } from '@/components/LocationCombobox'
import { Button } from '@/components/ui/button'

type Props = {
  pending: boolean
  onSubmit: (request: PlanRequest) => void
}

export function PlanForm({ pending, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)

  function submit(event: FormEvent) {
    event.preventDefault()
    if (origin && destination) onSubmit({ origin, destination })
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <LocationCombobox id="origin" label="Origin" value={origin} onChange={setOrigin} />
      <LocationCombobox id="destination" label="Destination" value={destination} onChange={setDestination} />
      <Button type="submit" disabled={!origin || !destination || pending}>
        {pending ? 'Finding route…' : 'Plan route'}
      </Button>
    </form>
  )
}
