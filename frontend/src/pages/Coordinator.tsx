import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import Logo from '../components/Logo'
import { unlockCoordinator,
  userMessage,
} from '../api'
import AgentActivity from './AgentActivity'
import RunSheet from './RunSheet'
import { coordinatorToken, setCoordinatorToken } from '../session'

/**
 * The admin screens are the only ones that show a family's home address,
 * email and phone number, so they sit behind a shared passcode. The passcode
 * is checked on the server; the browser only remembers the token it got back,
 * and only until the tab is closed.
 *
 * The show/hide control is there because this passcode is shared and typed by
 * someone who may be reading it off a note — hiding it by default is right,
 * refusing to ever show it is not.
 */
export default function Coordinator() {
  const [token, setToken] = useState<string | null>(coordinatorToken())
  const [passcode, setPasscode] = useState('')
  const [showPasscode, setShowPasscode] = useState(false)
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
      setError(userMessage(err, 'We could not check that just now. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <main className="page">
        <header className="page__nav"><Logo size={26} /></header>
        <h1 className="page__title">Admin</h1>
        <p className="page__blurb">
          These screens show families’ home addresses, emails and phone numbers,
          so they need the admin passcode.
        </p>
        <form className="form" onSubmit={submit}>
          <label className="field">
            <span className="field__label">Passcode</span>
            <span className="field__reveal">
              <input
                className="field__input" required autoFocus value={passcode}
                type={showPasscode ? 'text' : 'password'}
                onChange={(e) => setPasscode(e.target.value)}
              />
              <button
                type="button" className="field__eye"
                aria-label={showPasscode ? 'Hide passcode' : 'Show passcode'}
                aria-pressed={showPasscode}
                onClick={() => setShowPasscode((on) => !on)}
              >
                {showPasscode ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </span>
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
      <header className="page__nav"><Logo size={26} /></header>
      <p className="signed-in">
        Admin view unlocked
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
      <h1 className="page__title">Run sheet</h1>
      <p className="page__blurb">
        Expected drop-offs and deliveries, with contact details and statuses. These
        are the only screens that show a family’s address, email or phone number.
      </p>

      <RunSheet token={token} />

      <h2 className="activity__heading">Agent activity</h2>
      <p className="page__blurb">
        Every call the agents have made, in order: what went in, what came out, which
        tools ran, what the safety review removed, and what it cost.
      </p>

      <AgentActivity token={token} />
    </main>
  )
}
