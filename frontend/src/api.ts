export interface Ticket {
  id: number
  category: string
  issue_description: string
}

export interface TicketPage {
  total: number
  limit: number
  offset: number
  items: Ticket[]
}

export interface CategoryCount {
  category: string
  count: number
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, { signal })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return res.json()
}

export function fetchCategories() {
  return get<CategoryCount[]>('/api/categories')
}

export function fetchTickets(
  params: { q: string; category: string; limit: number; offset: number },
  signal?: AbortSignal,
) {
  const qs = new URLSearchParams({ limit: String(params.limit), offset: String(params.offset) })
  if (params.q) qs.set('q', params.q)
  if (params.category) qs.set('category', params.category)
  return get<TicketPage>(`/api/tickets?${qs}`, signal)
}
