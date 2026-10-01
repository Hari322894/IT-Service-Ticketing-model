import type { Ticket } from './api'

export default function TicketModal({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" role="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="ticket-head">
          <span className="id">Ticket #{ticket.id}</span>
          <span className="badge">{ticket.category}</span>
          <button className="close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <p className="full">{ticket.issue_description}</p>
      </div>
    </div>
  )
}
