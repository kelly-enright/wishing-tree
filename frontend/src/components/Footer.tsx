import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { getHealth, type Health } from '../api'
import { hours } from '../dates'

/**
 * A weekly window as a standing arrangement rather than one appointment:
 * "Thursday 4:00 PM-7:00 PM" becomes "Thursdays 4–7 PM". The day is plural
 * because it happens every week, which is the whole point of the footer.
 */
function recurring(windowLabel: string): string {
  const day = windowLabel.split(' ')[0]
  return `${day}s ${hours(windowLabel)}`
}

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
          <strong>{health.region.name}</strong> · Drop-off{' '}
          {recurring(health.region.dropoff_window)} at {health.region.hub_name}{' '}
          · Delivery {recurring(health.region.delivery_window)}
        </p>
      )}
      <p className="footer__note">
        No cash ever changes hands between neighbors. Wishing Tree pays rent and
        utilities directly to the landlord or provider.
      </p>
      <p className="footer__links">
        <Link to="/how-it-works">How it works</Link>
        <Link to="/about">About Wishing Tree</Link>
        <Link to="/coordinator">Admin</Link>
      </p>
    </footer>
  )
}
