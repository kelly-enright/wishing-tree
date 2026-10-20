import { useEffect, useState } from 'react'
import { getDeliveries, respondToWindow, type Delivery,
  userMessage,
} from '../api'

/**
 * What is on its way to this family, and the window to confirm.
 *
 * Saying the window does not work does not offer a new one. It flags the
 * delivery and a coordinator gets in touch — a date is a promise to a person,
 * and a person should make it.
 */
export default function Deliveries({ familyAlias }: { familyAlias: string }) {
  const [deliveries, setDeliveries] = useState<Delivery[] | null>(null)
  const [messages, setMessages] = useState<Record<number, string>>({})
  const [busy, setBusy] = useState<number | null>(null)

  useEffect(() => {
    getDeliveries(familyAlias).then((d) => setDeliveries(d.deliveries)).catch(() => setDeliveries([]))
  }, [familyAlias])

  if (!deliveries || deliveries.length === 0) return null

  async function answer(pledgeId: number, response: 'confirmed' | 'needs_reschedule') {
    setBusy(pledgeId)
    try {
      const result = await respondToWindow(familyAlias, pledgeId, response)
      setMessages((m) => ({ ...m, [pledgeId]: result.message }))
      setDeliveries((list) =>
        list!.map((d) => (d.pledge_id === pledgeId
          ? { ...d, window_response: result.window_response } : d)),
      )
    } catch (error) {
      setMessages((m) => ({ ...m, [pledgeId]: userMessage(error, 'We could not save that just now. Please try again.') }))
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className="deliveries" aria-label="Coming to you">
      <h2 className="deliveries__title">Coming to you</h2>

      {deliveries.map((delivery) => (
        <article key={delivery.pledge_id} className="delivery">
          <p className="delivery__item">{delivery.wish.item_description}</p>

          {delivery.paid_directly_to_provider ? (
            <p className="delivery__when">
              Paid directly to the provider on <strong>{delivery.delivery_date}</strong>.
              Nothing is delivered to you for this one.
            </p>
          ) : (
            <p className="delivery__when">
              Delivery on <strong>{delivery.delivery_date}</strong>, {delivery.delivery_window}.
            </p>
          )}

          {delivery.status === 'delivered' && (
            <p className="delivery__done">Delivered.</p>
          )}

          {delivery.status !== 'delivered' && !delivery.paid_directly_to_provider && (
            <>
              {delivery.window_response === 'pending' && (
                <div className="delivery__actions">
                  <button
                    type="button" className="btn btn--primary" disabled={busy === delivery.pledge_id}
                    onClick={() => answer(delivery.pledge_id, 'confirmed')}
                  >
                    Confirm delivery window
                  </button>
                  <button
                    type="button" className="btn btn--light" disabled={busy === delivery.pledge_id}
                    onClick={() => answer(delivery.pledge_id, 'needs_reschedule')}
                  >
                    This doesn’t work
                  </button>
                </div>
              )}

              {delivery.window_response === 'confirmed' && (
                <p className="delivery__confirmed">You confirmed this window.</p>
              )}

              {delivery.window_response === 'needs_reschedule' && (
                <p className="delivery__flagged">
                  A coordinator will reach out to reschedule.
                </p>
              )}
            </>
          )}

          {messages[delivery.pledge_id] && (
            <p className="delivery__message">{messages[delivery.pledge_id]}</p>
          )}
        </article>
      ))}
    </section>
  )
}
