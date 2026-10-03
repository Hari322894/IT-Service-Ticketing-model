import { useEffect, useState } from 'react'
import { fetchTickets, type CategoryCount, type Ticket, type TicketPage } from './api'

const PAGE_SIZE = 25

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

export default function BrowsePage({
  categories,
  onSelect,
}: {
  categories: CategoryCount[]
  onSelect: (t: Ticket) => void
}) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [offset, setOffset] = useState(0)
  const [page, setPage] = useState<TicketPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const q = useDebounced(query.trim(), 300)

  // Reset to the first page whenever the filters change.
  useEffect(() => setOffset(0), [q, category])

  useEffect(() => {
    const ctrl = new AbortController()
    setLoading(true)
    fetchTickets({ q, category, limit: PAGE_SIZE, offset }, ctrl.signal)
      .then((p) => {
        setPage(p)
        setError(null)
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message)
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setLoading(false)
      })
    return () => ctrl.abort()
  }, [q, category, offset])

  const total = page?.total ?? 0
  const allCount = categories.reduce((n, c) => n + c.count, 0)

  return (
    <div className="browse">
      <aside className="sidebar">
        <h2>Categories</h2>
        <ul>
          <li>
            <button className={category === '' ? 'active' : ''} onClick={() => setCategory('')}>
              <span>All</span>
              <span className="count">{allCount.toLocaleString()}</span>
            </button>
          </li>
          {categories.map((c) => (
            <li key={c.category}>
              <button
                className={category === c.category ? 'active' : ''}
                onClick={() => setCategory(c.category)}
              >
                <span>{c.category}</span>
                <span className="count">{c.count.toLocaleString()}</span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <div className="main">
        <input
          className="search"
          type="search"
          placeholder="Search ticket text, e.g. password reset"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        <div className="meta">
          {error ? (
            <span className="error">{error}</span>
          ) : (
            <span>
              {total.toLocaleString()} result{total === 1 ? '' : 's'}
              {loading && ' · loading…'}
            </span>
          )}
        </div>

        <ul className="tickets">
          {page?.items.map((t) => (
            <li key={t.id}>
              <button className="ticket" onClick={() => onSelect(t)}>
                <div className="ticket-head">
                  <span className="id">#{t.id}</span>
                  <span className="badge">{t.category}</span>
                </div>
                <p className="preview">{t.issue_description}</p>
              </button>
            </li>
          ))}
        </ul>

        {page && total > PAGE_SIZE && (
          <nav className="pager">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
              ← Prev
            </button>
            <span>
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total.toLocaleString()}
            </span>
            <button disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
              Next →
            </button>
          </nav>
        )}
      </div>
    </div>
  )
}
