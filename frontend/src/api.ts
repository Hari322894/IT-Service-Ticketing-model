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

export interface Source {
  id: number
  category: string
  score: number
}

export interface AskResponse {
  answer: string
  sources: Source[]
}

export function fetchTicket(id: number) {
  return get<Ticket>(`/api/tickets/${id}`)
}

export async function ask(question: string): Promise<AskResponse> {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed: ${res.status}`
    throw new Error(detail)
  }
  return res.json()
}
