import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHealth, type Health } from '../api'
import TopBar from '../components/TopBar'
import HowItWorks from '../components/HowItWorks'
import DonorHowItWorks from '../components/DonorHowItWorks'
import Footer from '../components/Footer'
import Monty from '../components/Monty'
import usePageTitle from '../usePageTitle'

/**
 * How it works, for somebody who has not signed up.
 *
 * Both sides on one page, built from the two boxes the signed-in screens
 * already use — so there is one explanation of each side in the app, not two
 * that can drift apart. Nothing here is new copy.
 */
export default function HowItWorksPage() {
  usePageTitle('How it works')
  const [health, setHealth] = useState<Health | null>(null)
  useEffect(() => { getHealth().then(setHealth).catch(() => setHealth(null)) }, [])

  return (
    <main className="page page--narrow">
      <TopBar />

      <div className="intake__title">
        <Monty size={46} />
        <h1 className="page__title">How it works</h1>
      </div>
      <p className="page__blurb">
        Two sides of the same tree. Everything moves through one weekly
        drop-off at Yale School of Management.
      </p>

      <section className="howpage">
        <h2 className="howpage__side">Making a wish</h2>
        <HowItWorks />
        <Link className="btn btn--primary" to="/family/signup">Make a wish</Link>
      </section>

      <section className="howpage">
        <h2 className="howpage__side">Granting a wish</h2>
        <DonorHowItWorks />
        <Link className="btn btn--gold" to="/donor/signup">Grant a wish</Link>
      </section>

      {/* Kelly's words, unchanged. Saying plainly what the AI does — and
          naming the part it does not do — is the point of the section. */}
      <section className="howpage">
        <h2 className="howpage__side">How we use AI</h2>
        <p className="page__blurb">
          AI helps turn what you share into a clear wish, checks every wish for
          personal details before anyone sees it, and suggests wishes that fit a
          wish granter's budget. People, not AI, coordinate every drop-off and
          delivery.
        </p>
      </section>

      {health && (
        <section className="howpage">
          <h2 className="howpage__side">Where and when</h2>
          <p className="page__blurb">
            Drop off at <strong>{health.region.hub_name}</strong>,{' '}
            {health.region.hub_address}.<br />
            Drop-off: {health.region.dropoff_window}.<br />
            Delivery: {health.region.delivery_window}.
          </p>
        </section>
      )}

      <Footer />
    </main>
  )
}
