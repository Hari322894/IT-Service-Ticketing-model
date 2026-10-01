import { useEffect, useState } from 'react'
import { fetchCategories, fetchTicket, type CategoryCount, type Ticket } from './api'
import Ask from './Ask'
import Browse from './Browse'
import TicketModal from './TicketModal'

type Tab = 'ask' | 'browse'

export default function App() {
  const [tab, setTab] = useState<Tab>('ask')
  const [categories, setCategories] = useState<CategoryCount[]>([])
  const [selected, setSelected] = useState<Ticket | null>(null)

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  const allCount = categories.reduce((n, c) => n + c.count, 0)

  function openTicket(id: number) {
    fetchTicket(id).then(setSelected).catch(() => {})
  }

  return (
    <div className="layout">
      <header className="header">
        <div>
          <h1>IT Ticket Explorer</h1>
          <p className="subtitle">
            RAG-powered insights over {allCount ? allCount.toLocaleString() : ''} enterprise IT support tickets
          </p>
        </div>
        <nav className="tabs">
          <button className={tab === 'ask' ? 'active' : ''} onClick={() => setTab('ask')}>
            Ask
          </button>
          <button className={tab === 'browse' ? 'active' : ''} onClick={() => setTab('browse')}>
            Browse
          </button>
        </nav>
      </header>

      {/* Both views stay mounted so switching tabs keeps chat history and filters */}
      <div hidden={tab !== 'ask'}>
        <Ask onOpenTicket={openTicket} />
      </div>
      <div hidden={tab !== 'browse'}>
        <Browse categories={categories} onSelect={setSelected} />
      </div>

      {selected && <TicketModal ticket={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
