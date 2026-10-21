import { useEffect, useRef, useState } from 'react'
import {
  approveIntake, sendIntakeMessage, startIntake,
  type DraftWish, type Usage, type WishOutcome,
  userMessage,
} from '../api'
import HowItWorks from '../components/HowItWorks'
import Collapsible from '../components/Collapsible'
import TopBar from '../components/TopBar'
import { Info, ListChecks, Sparkles } from 'lucide-react'

/** The neighbor's two halves live on one page, so the links scroll rather
 *  than switch. Smooth unless the reader has asked for less motion. */
function scrollTo(id: string) {
  const target = document.getElementById(id)
  if (!target) return
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
}
import Monty from '../components/Monty'
import Thinking from '../components/Thinking'
import TokenPanel from '../components/TokenPanel'
import { useSession } from '../session'
import NeedsSignIn, { PageLoading } from '../components/NeedsSignIn'
import { signOut, switchSide } from '../auth'
import MyWishes from './MyWishes'
import WishReview from './WishReview'
import usePageTitle from '../usePageTitle'

type Bubble = { who: 'family' | 'agent'; text: string }

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
      .catch((err) => setError(userMessage(err, 'We could not start a new chat just now. Please try again.')))
    // one intake per visit
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
      setError(userMessage(err, 'We could not submit your wishes just now. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="page page--wide">
      <TopBar
        links={[
          { label: 'My wishes', short: 'Wishes',
            icon: <ListChecks size={17} aria-hidden="true" />,
            onClick: () => scrollTo('mywishes'), active: true },
          { label: 'Make a wish', short: 'Ask',
            icon: <Sparkles size={17} aria-hidden="true" />,
            onClick: () => scrollTo('makeawish') },
          { label: 'About', short: 'About',
            icon: <Info size={17} aria-hidden="true" />, to: '/about' },
        ]}
        alias={session.alias} me={me}
        onSwitch={signOut} onSwitchSide={switchSide}
      />

      <MyWishes alias={session.alias} />

      <div className="intake" id="makeawish">
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
                <form className="composer" onSubmit={send}>
                  <input
                    className="field__input" value={input} disabled={busy}
                    placeholder="Tell us what would help…" maxLength={2000}
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
                {result.held === 0 ? 'On the tree' : 'Here’s what happened'}
              </h1>
              <p className="page__blurb">
                {result.published > 0 && (
                  <>{result.published} wish{result.published === 1 ? '' : 'es'} went through the
                  privacy and safety check and {result.published === 1 ? 'is' : 'are'} now visible
                  to neighbors. </>
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
                      {outcome.published ? 'On the tree' : 'Held'}
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

              <HowItWorks />

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
