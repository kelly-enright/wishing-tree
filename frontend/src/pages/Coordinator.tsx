import { useState } from 'react'
import { Link } from 'react-router-dom'
import { unlockCoordinator } from '../api'
import { isCoordinatorUnlocked, setCoordinatorUnlocked } from '../session'

/**
 * The coordinator screens are the only ones that show a family's home address
 * and phone number, so they sit behind a shared passcode. The passcode is
 * checked on the server; the browser only remembers that it succeeded, and
 * only until the tab is closed.
 */
export default function Coordinator() {
  const [unlocked, setUnlocked] = useState(isCoordinatorUnlocked())
  const [passcode, setPasscode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await unlockCoordinator(passcode)
      setCoordinatorUnlocked(true)
      setUnlocked(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  if (!unlocked) {
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
    <main className="page">
      <Link to="/" className="page__back">← Wishing Tree</Link>
      <p className="signed-in">
        Coordinator view unlocked
        <button
          type="button"
          className="signed-in__switch"
          onClick={() => {
            setCoordinatorUnlocked(false)
            setUnlocked(false)
          }}
        >
          Lock again
        </button>
      </p>
      <h1 className="page__title">This week’s run sheet</h1>
      <p className="page__blurb">
        This is where the coordinator will see expected drop-offs and deliveries for the
        week, with contact details and statuses.
      </p>
      <p className="page__tag">Coming in a later step of this build.</p>
    </main>
  )
}
