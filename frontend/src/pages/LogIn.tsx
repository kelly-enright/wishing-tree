import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { logIn, userMessage } from '../api'
import { homePath, setMe } from '../session'
import TopBar from '../components/TopBar'
import PasswordField from '../components/PasswordField'
import Footer from '../components/Footer'
import usePageTitle from '../usePageTitle'

/**
 * Log in.
 *
 * One email may hold both a neighbor and a wish granter account, so a
 * successful login does not always know where to send you — when it does
 * not, it hands over to the choose-a-side screen rather than guessing.
 *
 * The error says only that the email and password do not match. Which of the
 * two was wrong is exactly what somebody probing for accounts wants to know.
 */
export default function LogIn() {
  usePageTitle('Log in')
  // Where to go afterwards. Set when somebody tapped a wish on the landing
  // page before they had an account: they came for that wish, so that is
  // where they land, not on a tree of thirty with the job of finding it.
  const next = new URLSearchParams(useLocation().search).get('next')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const me = await logIn(email.trim(), password)
      setMe(me)
      if (me.must_choose) navigate(next ? `/choose?next=${encodeURIComponent(next)}` : '/choose')
      else if (next && me.role === 'donor') navigate(next)
      else navigate(homePath(me.role === 'donor' ? 'donor' : 'family'))
    } catch (err) {
      setError(userMessage(err, 'We could not log you in just now. Please try again.'))
      setBusy(false)
    }
  }

  return (
    <main className="page page--narrow">
      <TopBar />
      <h1 className="page__title">Log in</h1>
      <p className="page__blurb">
        {next ? "Log in and we'll take you straight back to that wish."
              : 'Welcome back.'}
      </p>

      <form className="form" onSubmit={submit}>
        <label className="field">
          <span className="field__label">Email</span>
          <input
            className="field__input" type="email" required autoFocus
            autoComplete="username" value={email} placeholder="you@example.com"
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <PasswordField value={password} onChange={setPassword} />

        {error && <p className="form__error" role="alert">{error}</p>}

        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
      </form>

      <p className="loginhelp">
        <Link to="/forgot">Forgot your password?</Link>
      </p>

      <p className="loginhelp">
        {next ? (
          <>New here? <Link to={`/donor/signup?next=${encodeURIComponent(next)}`}>
            Create an account</Link> and you can grant it.</>
        ) : (
          <>New here? <Link to="/family/signup">Make a wish</Link> or{' '}
          <Link to="/donor/signup">grant a wish</Link>.</>
        )}
      </p>

      <p className="loginhelp loginhelp--staff">
        <Link to="/coordinator">
          <ShieldCheck size={14} aria-hidden="true" /> Staff? Admin sign-in
        </Link>
      </p>

      <Footer />
    </main>
  )
}
