import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { ApiError } from './api/client'
import App from './App.tsx'

const queryClient = new QueryClient({
  defaultOptions: {
    // A 4xx, including a 429, would fail the same way again seconds later.
    queries: { retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2 },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
