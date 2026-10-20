import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getStats, listAccounts, type Account, type Stats } from '../api'
import Logo from '../components/Logo'
import Monty from '../components/Monty'
import { ServiceNotice } from '../components/ServiceArea'
import { clearSession, getSession, homePath, setSession } from '../session'

type Health = {
  region: { name: string; hub_name: string; dropoff_window: string; delivery_window: string }
}

const ROLES = [
  {
    to: '/family/signup',
    eyebrow: 'For neighbors',
    title: 'Make a wish',
    blurb: 'Something you or your family could use? Ask your neighbors.',
  },
  {
    to: '/donor/signup',
    eyebrow: 'For neighbors',
    title: 'Grant a wish',
    blurb: 'Help a neighbor with something they need.',
  },
  {
    to: '/coordinator',
    eyebrow: 'For staff',
    title: 'Admin',
    blurb: 'This week’s run sheet — who is dropping off, what is arriving, and what goes out on Saturday — plus what the agents have been doing.',
  },
]

export default function Landing() {
  const [health, setHealth] = useState<Health | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [accounts, setAccounts] = useState<{ families: Account[]; donors: Account[] } | null>(null)
  const [showAccounts, setShowAccounts] = useState(false)
  const [session, setLocalSession] = useState(getSession())
  const navigate = useNavigate()

  useEffect(() => { getStats().then(setStats).catch(() => setStats(null)) }, [])

  useEffect(() => {
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : null))
      .then(setHealth)
      .catch(() => setHealth(null))
  }, [])

  useEffect(() => {
    if (!showAccounts || accounts) return
    listAccounts().then(setAccounts).catch(() => setAccounts({ families: [], donors: [] }))
  }, [showAccounts, accounts])

  function continueAs(account: Account) {
    setSession({ role: account.role, alias: account.alias, zip: account.zip })
    navigate(homePath(account.role))
  }

  function signOut() {
    clearSession()
    setLocalSession(null)
  }

  return (
    <main className="landing">
      <header className="hero">
        <div className="hero__logo"><Logo plain size={52} /></div>
        <p className="hero__tagline">Grant a neighbor's wish, any time of year</p>
        <ServiceNotice />

        {stats && (
          <p className="hero__from">
            {stats.line}
            {stats.wishes_granted > 0 && (
              <>
                {' '}
                <strong>
                  {stats.wishes_granted} wish{stats.wishes_granted === 1 ? '' : 'es'} granted
                </strong>{' '}
                so far.
              </>
            )}
          </p>
        )}
        <p className="hero__lede">
          A giving tree that stays up all year in New Haven. Ask for what would
          actually help, or grant a wish for someone nearby. Everything moves
          through one weekly drop-off.
        </p>
        <div className="hero__monty">
          <Monty size={64} />
          <p className="hero__pick">
            Monty here. Pick the one that sounds like you.{' '}
            <Link className="hero__about" to="/about">Why we exist</Link>
          </p>
        </div>
      </header>

      {session && (
        <section className="welcome" aria-label="Signed in">
          <p className="welcome__text">
            This browser is signed in as <strong>{session.alias}</strong>.
          </p>
          <div className="welcome__actions">
            <Link className="btn btn--light" to={homePath(session.role)}>
              Continue
            </Link>
            <button type="button" className="btn btn--ghost" onClick={signOut}>
              Sign out
            </button>
          </div>
        </section>
      )}

      <section className="roles" aria-label="Choose how you want to start">
        {ROLES.map((role) => (
          <Link key={role.to} to={role.to} className="role">
            <span className="role__eyebrow">{role.eyebrow}</span>
            <span className="role__title">{role.title}</span>
            <span className="role__blurb">{role.blurb}</span>
            <span className="role__go" aria-hidden="true">Start here →</span>
          </Link>
        ))}
      </section>

      <section className="demo" aria-label="Demo shortcut">
        <div className="demo__header">
          <div>
            <p className="demo__tag">Demo shortcut — not part of the real product</p>
            <p className="demo__text">
              Continue as a neighbor who already has an account, without signing up.
            </p>
          </div>
          <button
            type="button"
            className="btn btn--light"
            onClick={() => setShowAccounts((open) => !open)}
            aria-expanded={showAccounts}
          >
            {showAccounts ? 'Hide accounts' : 'Continue as…'}
          </button>
        </div>

        {showAccounts && (
          <div className="accounts">
            {!accounts && <p className="accounts__loading">Loading accounts…</p>}
            {accounts && accounts.families.length === 0 && accounts.donors.length === 0 && (
              <p className="accounts__loading">
                No demo accounts yet — sign up above and you'll appear here.
              </p>
            )}
            {accounts && (
              <>
                <div className="accounts__group">
                  <h2 className="accounts__title">Making a wish</h2>
                  <ul className="accounts__list">
                    {accounts.families.map((account) => (
                      <li key={account.alias}>
                        <button type="button" className="account" onClick={() => continueAs(account)}>
                          <span className="account__alias">{account.alias}</span>
                          <span className="account__detail">
                            {account.zip} · {account.detail}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="accounts__group">
                  <h2 className="accounts__title">Granting a wish</h2>
                  <ul className="accounts__list">
                    {accounts.donors.map((account) => (
                      <li key={account.alias}>
                        <button type="button" className="account" onClick={() => continueAs(account)}>
                          <span className="account__alias">{account.alias}</span>
                          <span className="account__detail">
                            {account.zip} · {account.detail}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        )}
      </section>

      {health && (
        <footer className="footer">
          <p>
            <strong>{health.region.name}</strong> · Drop-off at {health.region.hub_name},{' '}
            {health.region.dropoff_window} · Delivery {health.region.delivery_window}
          </p>
          <p className="footer__note">
            No cash ever changes hands between neighbors. Rent and utilities are paid
            straight to the landlord or provider.
          </p>
          <p className="footer__links">
            <Link to="/about">About Wishing Tree</Link>
          </p>
        </footer>
      )}
    </main>
  )
}
