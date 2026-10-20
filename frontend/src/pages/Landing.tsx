import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listAccounts, type Account } from '../api'
import { clearSession, getSession, homePath, setSession } from '../session'

type Health = {
  region: { name: string; hub_name: string; dropoff_window: string; delivery_window: string }
}

const ROLES = [
  {
    to: '/family/signup',
    eyebrow: 'For families',
    title: 'I need help',
    blurb: 'Tell us what you need in your own words. We turn it into wishes you approve before anyone sees them.',
  },
  {
    to: '/donor/signup',
    eyebrow: 'For neighbours',
    title: 'I want to give',
    blurb: 'Browse wishes near you, or get matched to the ones your budget and interests fit best.',
  },
  {
    to: '/coordinator',
    eyebrow: 'For staff',
    title: 'Coordinator',
    blurb: 'See this week’s run sheet: who is dropping off, what is arriving, and what goes out on Saturday.',
  },
]

export default function Landing() {
  const [health, setHealth] = useState<Health | null>(null)
  const [accounts, setAccounts] = useState<{ families: Account[]; donors: Account[] } | null>(null)
  const [showAccounts, setShowAccounts] = useState(false)
  const [session, setLocalSession] = useState(getSession())
  const navigate = useNavigate()

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
        <p className="hero__eyebrow">New Haven, CT</p>
        <h1 className="hero__title">
          Wishing <span className="hero__accent">Tree</span>
        </h1>
        <p className="hero__lede">
          A giving tree that stays up all year. Families ask for what they actually need,
          neighbours grant a wish, and everything moves through one weekly drop-off.
        </p>
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
            <span className="role__go" aria-hidden="true">Start →</span>
          </Link>
        ))}
      </section>

      <section className="demo" aria-label="Demo shortcut">
        <div className="demo__header">
          <div>
            <p className="demo__tag">Demo shortcut — not part of the real product</p>
            <p className="demo__text">
              Continue as an existing family or donor, without signing up or typing anything.
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
            {accounts && (
              <>
                <div className="accounts__group">
                  <h2 className="accounts__title">Families</h2>
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
                  <h2 className="accounts__title">Donors</h2>
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
            No cash ever changes hands between neighbours. Rent and utilities are paid
            directly to the landlord or provider.
          </p>
        </footer>
      )}
    </main>
  )
}
