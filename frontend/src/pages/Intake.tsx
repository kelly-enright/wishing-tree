import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  approveIntake, sendIntakeMessage, startIntake,
  type DraftWish, type Usage, type WishOutcome,
} from '../api'
import TokenPanel from '../components/TokenPanel'
import { clearSession, getSession } from '../session'
import WishReview from './WishReview'

type Bubble = { who: 'family' | 'agent'; text: string }

export default function Intake() {
  const session = getSession()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [bubbles, setBubbles] = useState<Bubble[]>([])
  const [drafts, setDrafts] = useState<DraftWish[]>([])
  const [input, setInput] = useState('')
  const [usage, setUsage] = useState<Usage | null>(null)
  const [turnsLeft, setTurnsLeft] = useState<number | null>(null)
  const [phase, setPhase] = useState<'chat' | 'review' | 'done'>('chat')
  const [atCap, setAtCap] = useState(false)
  const [stopped, setStopped] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ published: number; held: number; seconds: number; outcomes: WishOutcome[] } | null>(null)
  const transcript = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!session) return
    startIntake(session.alias)
      .then((start) => {
        setSessionId(start.session_id)
        setAtCap(start.at_wish_cap)
        setBubbles([{ who: 'agent', text: start.message }])
        setTurnsLeft(start.turns_remaining ?? null)
        if (start.usage) setUsage(start.usage)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not start.'))
    // one intake per visit
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    transcript.current?.scrollTo({ top: transcript.current.scrollHeight, behavior: 'smooth' })
  }, [bubbles, busy])

  if (!session || session.role !== 'family') {
    return (
      <main className="page">
        <Link to="/" className="page__back">← Wishing Tree</Link>
        <h1 className="page__title">Sign in first</h1>
        <p className="page__blurb">
          <Link to="/family/signup">Create a family account</Link> to start an intake.
        </p>
      </main>
    )
  }

  async function send(event: React.FormEvent) {
    event.preventDefault()
    const text = input.trim()
    if (!text || !sessionId || busy) return

    setBubbles((b) => [...b, { who: 'family', text }])
    setInput('')
    setBusy(true)
    setError(null)

    try {
      const turn = await sendIntakeMessage(sessionId, text)
      setBubbles((b) => [...b, { who: 'agent', text: turn.message }])
      setDrafts(turn.draft_wishes)
      setUsage(turn.usage)
      setTurnsLeft(turn.turns_remaining)
      if (turn.limit_reached) setStopped(true)
      // Only move on when there is something to look at. A chat that stopped
      // with nothing drafted should leave its last message on screen.
      if ((turn.done || turn.limit_reached) && turn.draft_wishes.length > 0) {
        setPhase('review')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  async function approve() {
    if (!sessionId) return
    setBusy(true)
    setError(null)
    try {
      // Sent exactly as drafted. A wish with no date keeps no date.
      const done = await approveIntake(sessionId, drafts)
      setUsage(done.usage)
      setResult({
        published: done.published,
        held: done.held,
        seconds: done.duration_seconds,
        outcomes: done.outcomes,
      })
      setPhase('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="page page--wide">
      <Link to="/" className="page__back">← Wishing Tree</Link>

      <p className="signed-in">
        Signed in as <strong>{session.alias}</strong> · {session.zip}
        <button
          type="button" className="signed-in__switch"
          onClick={() => { clearSession(); window.location.assign('/') }}
        >
          Switch account
        </button>
      </p>

      <div className="intake">
        <div className="intake__main">
          {phase === 'chat' && (
            <>
              <h1 className="page__title">Tell us what you need</h1>
              <div className="transcript" ref={transcript}>
                {bubbles.map((bubble, i) => (
                  <p key={i} className={`bubble bubble--${bubble.who}`}>{bubble.text}</p>
                ))}
                {busy && <p className="bubble bubble--agent bubble--thinking">Thinking…</p>}
              </div>

              {error && <p className="form__error" role="alert">{error}</p>}

              {!atCap && !stopped && (
                <form className="composer" onSubmit={send}>
                  <input
                    className="field__input" value={input} disabled={busy}
                    placeholder="Type here…" maxLength={2000}
                    onChange={(e) => setInput(e.target.value)}
                  />
                  <button className="btn btn--primary" type="submit" disabled={busy || !input.trim()}>
                    Send
                  </button>
                </form>
              )}

              <div className="intake__footer">
                {stopped && (
                  <span className="intake__stopped">
                    This chat has stopped. Anything already drafted is safe.
                  </span>
                )}
                {turnsLeft !== null && !atCap && !stopped && (
                  <span>{turnsLeft} message{turnsLeft === 1 ? '' : 's'} left in this chat</span>
                )}
                {drafts.length > 0 && (
                  <button type="button" className="btn btn--light" onClick={() => setPhase('review')}>
                    Review {drafts.length} wish{drafts.length === 1 ? '' : 'es'} →
                  </button>
                )}
              </div>
            </>
          )}

          {phase === 'review' && (
            <>
              <h1 className="page__title">Check your wishes</h1>
              <button type="button" className="page__back" onClick={() => setPhase('chat')}>
                ← Back to the chat
              </button>
              <WishReview
                wishes={drafts}
                busy={busy}
                error={error}
                onChange={(i, patch) =>
                  setDrafts((d) => d.map((w, j) => (j === i ? { ...w, ...patch } : w)))}
                onRemove={(i) => setDrafts((d) => d.filter((_, j) => j !== i))}
                onApprove={approve}
              />
            </>
          )}

          {phase === 'done' && result && (
            <>
              <h1 className="page__title">
                {result.held === 0 ? 'On the wish wall' : 'Here’s what happened'}
              </h1>
              <p className="page__blurb">
                {result.published > 0 && (
                  <>{result.published} wish{result.published === 1 ? '' : 'es'} went through the
                  privacy and safety check and {result.published === 1 ? 'is' : 'are'} now visible
                  to neighbours. </>
                )}
                {result.held > 0 && (
                  <>{result.held} {result.held === 1 ? 'wish is' : 'wishes are'} being held for a
                  coordinator to look at. {result.held === 1 ? 'It is' : 'They are'} not public.</>
                )}
              </p>

              <ul className="outcomes">
                {result.outcomes.map((outcome) => (
                  <li
                    key={outcome.request_id}
                    className={`outcome outcome--${outcome.published ? 'published' : 'held'}`}
                  >
                    <span className="outcome__status">
                      {outcome.published ? 'On the wall' : 'Held'}
                    </span>
                    <p className="outcome__desc">{outcome.description}</p>
                    <p className="outcome__note">{outcome.note_to_family}</p>
                    {outcome.removed.length > 0 && (
                      <p className="outcome__removed">
                        Taken out before anyone sees it: {outcome.removed.join(', ')}.
                      </p>
                    )}
                  </li>
                ))}
              </ul>

              <p className="page__tag">
                This intake took {Math.round(result.seconds)} seconds from first message to approval.
              </p>
            </>
          )}
        </div>

        <TokenPanel usage={usage} />
      </div>
    </main>
  )
}
