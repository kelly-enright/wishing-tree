/**
 * Three steps, on the family's first screen and again after posting.
 *
 * The third step says plainly that a wish is not guaranteed. Someone asking
 * for help deserves to know that before they hope.
 */
export default function HowItWorks({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`how${compact ? ' how--compact' : ''}`} aria-label="How it works">
      <h2 className="how__title">How it works</h2>
      <ol className="how__steps">
        <li>
          <span className="how__num">1</span>
          <span className="how__text">
            <strong>Tell us what you need.</strong> In your own words — we'll turn
            it into wishes you check first.
          </span>
        </li>
        <li>
          <span className="how__num">2</span>
          <span className="how__text">
            <strong>We check it for privacy and post it on the Wishing Tree.</strong>{' '}
            Names, addresses and anything identifying come out before anyone sees it.
          </span>
        </li>
        <li>
          <span className="how__num">3</span>
          <span className="how__text">
            <strong>A neighbor nearby grants it, and we deliver it to your door on a
            Saturday.</strong> We can't promise every wish finds someone — but most do,
            and nothing is lost if one doesn't.
          </span>
        </li>
      </ol>
    </section>
  )
}
