import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

type Health = {
  status: string
  region: { name: string; hub_name: string; dropoff_window: string; delivery_window: string }
}

const ROLES = [
  {
    to: '/family',
    eyebrow: 'For families',
    title: 'I need help',
    blurb: 'Tell us what you need in your own words. We turn it into wishes you approve before anyone sees them.',
  },
  {
    to: '/donor',
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

  useEffect(() => {
    fetch('/api/health')
      .then((r) => (r.ok ? r.json() : null))
      .then(setHealth)
      .catch(() => setHealth(null))
  }, [])

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

      <section className="demo">
        <p className="demo__text">
          Just looking around? Open a seeded demo family with wishes already on the wall.
        </p>
        <Link to="/family/demo" className="demo__link">
          Open a demo family
        </Link>
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
