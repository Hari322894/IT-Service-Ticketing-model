import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { fetchCategories, fetchTicket, type CategoryCount, type Ticket } from './api'
import AskPage from './AskPage'
import BrowsePage from './BrowsePage'
import HomePage from './HomePage'
import TicketModal from './TicketModal'

export default function App() {
  // The URL decides which page shows: /ask, /browse, or the homepage for anything else
  const { pathname } = useLocation()
  const tab = pathname === '/ask' ? 'ask' : pathname === '/browse' ? 'browse' : 'home'
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
        <Link to="/" className="logo">
          <h1>IT Ticket Explorer</h1>
          <p className="subtitle">
            RAG-powered insights over {allCount ? allCount.toLocaleString() : ''} enterprise IT support tickets
          </p>
        </Link>
      </header>

      {tab === 'home' && <HomePage />}
      {/* Ask and Browse stay mounted so switching pages keeps chat history and filters */}
      <div hidden={tab !== 'ask'}>
        <AskPage onOpenTicket={openTicket} />
      </div>
      <div hidden={tab !== 'browse'}>
        <BrowsePage categories={categories} onSelect={setSelected} />
      </div>

      {selected && <TicketModal ticket={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
