import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { resetPassword, userMessage } from '../api'
import TopBar from '../components/TopBar'
import PasswordField from '../components/PasswordField'
import Footer from '../components/Footer'
import usePageTitle from '../usePageTitle'

/**
 * Forgotten password.
 *
 * Wishing Tree sends no email, so there is no link to click. A coordinator
 * issues a one-time code and reads it out; this screen is where it is spent.
 * Someone who has not got a code yet is told plainly who to ask, rather than
 * being left at a form they cannot fill in.
 */
export default function Forgot() {
  usePageTitle('Forgot your password?')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await resetPassword(email.trim(), code.trim().toUpperCase(), password)
      setDone(true)
    } catch (err) {
      setError(userMessage(err, 'We could not reset your password just now.'))
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <main className="page page--narrow">
        <TopBar />
        <h1 className="page__title">Your password is set</h1>
        <p className="page__blurb">You can log in with it now.</p>
        <button className="btn btn--primary" type="button" onClick={() => navigate('/login')}>
          Log in
        </button>
        <Footer />
      </main>
    )
  }

  return (
    <main className="page page--narrow">
      <TopBar />
      <h1 className="page__title">Forgot your password?</h1>
      <p className="page__blurb">
        Ask a Wishing Tree coordinator and they'll give you a one-time code.
        You can reach them at a drop-off, or on delivery day. We don't send
        emails, so there's no link to look for.
      </p>

      <form className="form" onSubmit={submit}>
        <label className="field">
          <span className="field__label">Email</span>
          <input
            className="field__input" type="email" required autoComplete="username"
            value={email} placeholder="you@example.com"
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Code from the coordinator</span>
          <input
            className="field__input code" required value={code}
            placeholder="ABCD-2345" autoCapitalize="characters" spellCheck={false}
            onChange={(e) => setCode(e.target.value)}
          />
          <span className="field__hint">It works once, and expires within the hour.</span>
        </label>

        <PasswordField
          value={password} onChange={setPassword} isNew label="New password"
          hint="At least 8 characters."
        />

        {error && <p className="form__error" role="alert">{error}</p>}

        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? 'Setting it…' : 'Set my password'}
        </button>
      </form>

      <p className="loginhelp"><Link to="/login">Back to log in</Link></p>
      <Footer />
    </main>
  )
}
