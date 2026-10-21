import { useCallback, useEffect, useRef, useState } from 'react'
import {
  approveIntake, sendIntakeMessage, startIntake,
  type DraftWish, type Usage, type WishOutcome,
  userMessage,
} from '../api'
import HowItWorks from '../components/HowItWorks'
import Collapsible from '../components/Collapsible'
import TopBar, { neighborLinks } from '../components/TopBar'
import WishCard from '../components/WishCard'
import { Link } from 'react-router-dom'
import Monty from '../components/Monty'
import Thinking from '../components/Thinking'
import TokenPanel from '../components/TokenPanel'
import { useSession } from '../session'
import NeedsSignIn, { PageLoading } from '../components/NeedsSignIn'
import { signOut, switchSide } from '../auth'
import WishReview from './WishReview'
import usePageTitle from '../usePageTitle'

type Bubble = { who: 'family' | 'agent'; text: string }

/** Ideas, for the blank-page moment. Tapping one fills the box rather than
 *  sending it, so somebody can add the detail that makes it their wish. */
const STARTERS = [
  'Clothes or a coat',
  'School supplies',
  'Help with a bill',
  'A birthday gift',
  'Something for the home',
]

export default function Intake() {
  usePageTitle('Make a wish')
  const { session, me, loading } = useSession()
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
  const box = useRef<HTMLInputElement>(null)

  /** Open a chat. Called on arrival, and again for a second wish. */
  const begin = useCallback(() => {
    if (!session) return
    startIntake(session.alias)
      .then((start) => {
        setSessionId(start.session_id)
        setAtCap(start.at_wish_cap)
        setBubbles([{ who: 'agent', text: start.message }])
        setTurnsLeft(start.turns_remaining ?? null)
        if (start.usage) setUsage(start.usage)
      })
      .catch((err) => setError(userMessage(err, 'We could not start a new chat just now. Please try again.')))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.alias])

  useEffect(() => { begin() }, [begin])

  useEffect(() => {
    transcript.current?.scrollTo({ top: transcript.current.scrollHeight, behavior: 'smooth' })
  }, [bubbles, busy])

  if (loading) return <PageLoading />
  if (!session || session.role !== 'family') {
    return <NeedsSignIn want="family" />
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
      setError(userMessage(err, 'That message did not get through. Please try again.'))
    } finally {
      // Back in the box, both after sending and once the reply lands. On a
      // phone this is what keeps the keyboard up: the field never loses
      // focus, so the browser never has a reason to close it. It has to
      // happen in `finally`, because a failed send is exactly the moment
      // somebody wants to type again.
      setBusy(false)
      box.current?.focus()
    }
  }

  /** Start a second wish from the confirmation, with nothing carried over. */
  function startAgain() {
    setBubbles([])
    setDrafts([])
    setResult(null)
    setInput('')
    setError(null)
    setStopped(false)
    setSessionId(null)
    setPhase('chat')
    begin()
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
      setError(userMessage(err, 'We could not submit your wishes just now. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="page page--wide">
      <TopBar
        links={neighborLinks('new')}
        alias={session.alias} me={me}
        onSwitch={signOut} onSwitchSide={switchSide}
      />

      <div className="intake">
        <div className="intake__main">
          {phase === 'chat' && (
            <>
              <div className="intake__title">
                {/* Calm on this side: present, but not performing. */}
                <Monty size={46} mood="calm" />
                <h1 className="page__title">Make a wish</h1>
              </div>
              {bubbles.length <= 1 && (
                <Collapsible id="family-how" title="How it works">
                  <HowItWorks compact />
                </Collapsible>
              )}
              <div className="transcript" ref={transcript}>
                {/* Monty sits beside what the agent says, and nothing sits
                    beside what the neighbor says. It is the plainest way to
                    show which half of this conversation is a machine. */}
                {bubbles.map((bubble, i) => (
                  <div key={i} className={`turn turn--${bubble.who}`}>
                    {bubble.who === 'agent' && (
                      <span className="turn__avatar" aria-hidden="true">
                        <Monty size={28} mood="calm" />
                      </span>
                    )}
                    <p className={`bubble bubble--${bubble.who}`}>{bubble.text}</p>
                  </div>
                ))}
                {busy && (
                  <div className="turn turn--agent">
                    <span className="turn__avatar" aria-hidden="true">
                      <Monty size={28} mood="calm" />
                    </span>
                    <div className="bubble bubble--agent bubble--thinking">
                      <Thinking label="Reading what you wrote" />
                    </div>
                  </div>
                )}
              </div>

              {error && <p className="form__error" role="alert">{error}</p>}

              {!atCap && !stopped && (
                <>
                {bubbles.length <= 1 && (
                  <div className="starters" role="group" aria-label="Ideas to start with">
                    {STARTERS.map((starter) => (
                      <button
                        key={starter} type="button" className="chip"
                        onClick={() => { setInput(starter); box.current?.focus() }}
                      >
                        {starter}
                      </button>
                    ))}
                  </div>
                )}

                <form className="composer" onSubmit={send}>
                  {/* `readOnly`, not `disabled`: a disabled field loses
                      focus the moment it is disabled, and on a phone that
                      closes the keyboard mid-sentence. This one stays
                      focused while the agent is thinking, and simply will
                      not accept a second message until the reply lands. */}
                  <input
                    ref={box}
                    className="field__input" value={input} readOnly={busy}
                    placeholder="Tell us what would help…" maxLength={2000}
                    onChange={(e) => setInput(e.target.value)}
                  />
                  <button className="btn btn--primary" type="submit" disabled={busy || !input.trim()}>
                    Send
                  </button>
                </form>
                </>
              )}

              <div className="intake__footer">
                {stopped && (
                  <span className="intake__stopped">
                    This chat has stopped. Anything already drafted is safe.
                  </span>
                )}
                {/* Counting down from twenty tells someone their help is
                    rationed before it ever is. Five is close enough to be
                    worth knowing. */}
                {turnsLeft !== null && turnsLeft <= 5 && !atCap && !stopped && (
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
              {busy && (
                <Thinking label="Checking these over before anyone sees them" />
              )}
              <WishReview
                wishes={drafts}
                alias={session.alias}
                busy={busy}
                error={error}
                onChange={(i, patch) =>
                  setDrafts((d) => d.map((w, j) => (j === i ? { ...w, ...patch } : w)))}
                onRemove={(i) => setDrafts((d) => d.filter((_, j) => j !== i))}
                onApprove={approve}
                onBack={() => setPhase('chat')}
              />
            </>
          )}

          {phase === 'done' && result && (
            <>
              <h1 className="page__title">
                {result.published > 0
                  ? result.published === 1
                    ? 'Your wish is on the tree!'
                    : 'Your wishes are on the tree!'
                  : 'Thanks — we have your wish'}
              </h1>

              {result.published > 0 && (
                <p className="page__blurb">
                  We'll email you when a neighbor picks your wish.
                </p>
              )}

              <ul className="outcomes">
                {result.outcomes.map((outcome) => (
                  <li
                    key={outcome.request_id}
                    className={`outcome outcome--${outcome.published ? 'published' : 'held'}`}
                  >
                    <span className={`track__stage track__stage--${
                      outcome.published ? 'on_the_tree' : 'not_posted'}`}>
                      {outcome.published ? 'On the tree' : 'Not on the tree yet'}
                    </span>
                    {outcome.card
                      ? <WishCard wish={outcome.card} />
                      : <p className="outcome__desc">{outcome.description}</p>}

                    {/* Our sentence, naming the reason and what to change.
                        The agent's own wording stays in Agent activity. */}
                    {!outcome.published && outcome.held_reason && (
                      <p className="outcome__note">{outcome.held_reason}</p>
                    )}

                    {outcome.removed.length > 0 && (
                      <p className="outcome__removed">
                        Taken out before anyone saw it: {outcome.removed.join(', ')}.
                      </p>
                    )}
                  </li>
                ))}
              </ul>

              <div className="review__actions">
                <button
                  type="button" className="btn btn--primary"
                  onClick={startAgain}
                >
                  Make another wish
                </button>
                <Link className="btn btn--light" to="/family">See all my wishes</Link>
              </div>
            </>
          )}
        </div>

        <TokenPanel usage={usage} />
      </div>
    </main>
  )
}
