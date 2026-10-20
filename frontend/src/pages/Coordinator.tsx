import { useState } from 'react'
import { Link } from 'react-router-dom'
import { unlockCoordinator } from '../api'
import AgentActivity from './AgentActivity'
import { coordinatorToken, setCoordinatorToken } from '../session'

/**
 * The coordinator screens are the only ones that show a family's home address
 * and phone number, so they sit behind a shared passcode. The passcode is
 * checked on the server; the browser only remembers that it succeeded, and
 * only until the tab is closed.
 */
export default function Coordinator() {
  const [token, setToken] = useState<string | null>(coordinatorToken())
  const [passcode, setPasscode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const unlocked = await unlockCoordinator(passcode)
      setCoordinatorToken(unlocked.token)
      setToken(unlocked.token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <main className="page">
        <Link to="/" className="page__back">← Wishing Tree</Link>
        <h1 className="page__title">Coordinator</h1>
        <p className="page__blurb">
          These screens show families’ home addresses and phone numbers, so they need
          the coordinator passcode.
        </p>
        <form className="form" onSubmit={submit}>
          <label className="field">
            <span className="field__label">Passcode</span>
            <input
              className="field__input" type="password" required autoFocus
              value={passcode} onChange={(e) => setPasscode(e.target.value)}
            />
          </label>
          {error && <p className="form__error" role="alert">{error}</p>}
          <button className="btn btn--primary" type="submit" disabled={busy}>
            {busy ? 'Checking…' : 'Unlock'}
          </button>
        </form>
      </main>
    )
  }

  return (
    <main className="page page--wide">
      <Link to="/" className="page__back">← Wishing Tree</Link>
      <p className="signed-in">
        Coordinator view unlocked
        <button
          type="button"
          className="signed-in__switch"
          onClick={() => {
            setCoordinatorToken(null)
            setToken(null)
          }}
        >
          Lock again
        </button>
      </p>
      <h1 className="page__title">Agent activity</h1>
      <p className="page__blurb">
        Every call the agents have made, in order: what went in, what came out, which
        tools ran, what the safety review removed, and what it cost.
      </p>

      <AgentActivity token={token} />

      <h2 className="activity__heading">This week’s run sheet</h2>
      <p className="page__blurb">
        Expected drop-offs and deliveries, with contact details and statuses.
      </p>
      <p className="page__tag">Coming in a later step of this build.</p>
    </main>
  )
}
