import { Button } from '@/components/ui/button'

type Props = { onTryExample: () => void }

/** What the app does, before the first plan. */
export function EmptyState({ onTryExample }: Props) {
  return (
    <section aria-label="About Spotter" className="flex flex-col gap-3 rounded-lg border border-dashed p-4 text-sm">
      <p className="font-medium">Find the safest way through the weather</p>
      <p className="text-muted-foreground">
        Spotter compares up to three truck routes. It checks the forecast at each checkpoint for the hour you get there,
        weighs it against your load and recommends the safest route.
      </p>
      <Button type="button" variant="outline" onClick={onTryExample}>
        Try an example: Denver to Chicago
      </Button>
    </section>
  )
}
