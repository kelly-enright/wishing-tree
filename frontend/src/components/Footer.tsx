import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getHealth, type Health } from '../api'

/**
 * The same footer on every page.
 *
 * It carries the two standing facts — where and when things move, and that no
 * cash passes between neighbors — plus the links that are always available.
 * Admin is here as well as on the login page, because staff arrive from both.
 */
export default function Footer() {
  const [health, setHealth] = useState<Health | null>(null)
  useEffect(() => { getHealth().then(setHealth).catch(() => setHealth(null)) }, [])

  return (
    <footer className="footer">
      {health && (
        <p>
          <strong>{health.region.name}</strong> · Drop-off at {health.region.hub_name},{' '}
          {health.region.dropoff_window} · Delivery {health.region.delivery_window}
        </p>
      )}
      <p className="footer__note">
        No cash ever changes hands between neighbors. Rent and utilities are paid
        straight to the landlord or provider.
      </p>
      <p className="footer__links">
        <Link to="/how-it-works">How it works</Link>
        <Link to="/about">About Wishing Tree</Link>
        <Link to="/coordinator">Admin</Link>
      </p>
    </footer>
  )
}
