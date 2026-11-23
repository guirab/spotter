import { useQuery, type QueryStatus } from '@tanstack/react-query'
import { apiGet } from '@/api/client'
import type { Health } from '@/api/types'

function healthLabel(status: QueryStatus, ok?: boolean) {
  if (status === 'pending') return 'Checking API…'
  if (status === 'error') return 'API unreachable'
  if (!ok) return 'API unhealthy'
  return 'API healthy'
}

export default function App() {
  const { data, status } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiGet<Health>('/api/health'),
  })

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-2 p-4">
      <h1 className="text-2xl font-semibold">Spotter</h1>
      <p role="status" className="text-muted-foreground">
        {healthLabel(status, data?.ok)}
      </p>
    </main>
  )
}
