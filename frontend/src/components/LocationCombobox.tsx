import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ChevronsUpDown } from 'lucide-react'
import { useEffect, useState } from 'react'
import { apiGet } from '@/api/client'
import type { Place } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

const MIN_CHARS = 3
const DEBOUNCE_MS = 300

function useDebouncedValue<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(timer)
  }, [value, ms])
  return debounced
}

type Props = {
  id: string
  label: string
  value: Place | null
  onChange: (place: Place) => void
}

export function LocationCombobox({ id, label, value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const term = search.trim().toLowerCase()
  const query = useDebouncedValue(term, DEBOUNCE_MS)

  const { data: places = [], isFetching, isError } = useQuery({
    queryKey: ['geocode', query],
    queryFn: () => apiGet<Place[]>(`/api/geocode?q=${encodeURIComponent(query)}`),
    enabled: query.length >= MIN_CHARS,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  })

  let emptyText = 'No US places found.'
  if (term.length < MIN_CHARS) emptyText = `Type at least ${MIN_CHARS} characters.`
  else if (isFetching || query !== term) emptyText = 'Searching…'
  else if (isError) emptyText = 'Search failed. Try again.'

  return (
    <div className="flex flex-col gap-1.5">
      <span id={`${id}-label`} className="text-sm font-medium">
        {label}
      </span>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            variant="outline"
            role="combobox"
            aria-expanded={open}
            aria-labelledby={`${id}-label ${id}`}
            className="justify-between font-normal"
          >
            <span className="truncate">{value?.label ?? 'Search a US place…'}</span>
            <ChevronsUpDown className="opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-(--radix-popover-trigger-width) p-0" align="start">
          <Command shouldFilter={false}>
            <CommandInput placeholder="City or address" value={search} onValueChange={setSearch} />
            <CommandList>
              <CommandEmpty>{emptyText}</CommandEmpty>
              {term.length >= MIN_CHARS &&
                places.map((place) => {
                  const key = `${place.label}|${place.lat}|${place.lon}`
                  return (
                    <CommandItem
                      key={key}
                      value={key}
                      onSelect={() => {
                        onChange(place)
                        setOpen(false)
                      }}
                    >
                      {place.label}
                    </CommandItem>
                  )
                })}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  )
}
