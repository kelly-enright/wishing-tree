import { weekly } from '../dates'

/**
 * Where a gift goes after someone grants a wish.
 *
 * The times are said the way a person says them — "Thursdays 4–7 PM", not
 * "Thursday 4:00 PM-7:00 PM" — and the day is plural because it is every
 * week. A singular "Thursday" reads as one particular Thursday.
 */
export default function HowItArrives({ region }: {
  region: { hub_name: string; hub_address: string; dropoff_window: string; delivery_window: string }
}) {
  return (
    <aside className="hubcard" aria-label="How it arrives">
      <h2 className="hubcard__title">How it arrives</h2>
      <p>Drop off at <strong>{region.hub_name}</strong>, {region.hub_address}.</p>
      <p>Drop-off: {weekly(region.dropoff_window)}</p>
      <p>Delivery: {weekly(region.delivery_window)}</p>
      <p className="hubcard__note">
        Wishing Tree pays rent and utilities directly to the landlord or
        provider, never cash to a neighbor.
      </p>
    </aside>
  )
}
