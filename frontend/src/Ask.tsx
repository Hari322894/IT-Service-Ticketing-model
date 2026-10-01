import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ask, type Source } from './api'

interface Turn {
  question: string
  answer?: string
  sources?: Source[]
  error?: string
}

const EXAMPLES = [
  'What issues are users reporting about password resets or expiring accounts?',
  'What are the most common hardware failures?',
  'Which storage problems come up repeatedly?',
]

export default function Ask({ onOpenTicket }: { onOpenTicket: (id: number) => void }) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [turns])

  async function submit(question: string) {
    question = question.trim()
    if (question.length < 3 || pending) return
    setInput('')
    setPending(true)
    setTurns((t) => [...t, { question }])
    try {
      const res = await ask(question)
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, ...res } : turn)))
    } catch (e) {
      const error = e instanceof Error ? e.message : String(e)
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, error } : turn)))
    } finally {
      setPending(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    submit(input)
  }

  return (
    <div className="ask">
      {turns.length === 0 && (
        <div className="empty">
          <p>Ask a question about the IT ticket history. Answers come only from matching tickets.</p>
          <div className="examples">
            {EXAMPLES.map((ex) => (
              <button key={ex} onClick={() => submit(ex)}>
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="turns">
        {turns.map((turn, i) => (
          <div key={i} className="turn">
            <div className="question">{turn.question}</div>
            {turn.error ? (
              <div className="answer error">{turn.error}</div>
            ) : turn.answer === undefined ? (
              <div className="answer muted">Searching tickets and generating an answer…</div>
            ) : (
              <div className="answer">
                <p className="full">{turn.answer}</p>
                {turn.sources && turn.sources.length > 0 && (
                  <div className="sources">
                    <span className="muted">Sources:</span>
                    {turn.sources.map((s) => (
                      <button key={s.id} className="source" onClick={() => onOpenTicket(s.id)}>
                        #{s.id} · {s.category} · {Math.round(s.score * 100)}%
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form className="ask-form" onSubmit={onSubmit}>
        <input
          className="search"
          placeholder="Ask about the tickets…"
          value={input}
          maxLength={500}
          onChange={(e) => setInput(e.target.value)}
          disabled={pending}
        />
        <button className="primary" type="submit" disabled={pending || input.trim().length < 3}>
          Ask
        </button>
      </form>
    </div>
  )
}
