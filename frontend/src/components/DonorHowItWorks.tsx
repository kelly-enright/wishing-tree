/**
 * Three steps for a donor. The third one is the part people ask about, so it
 * says it outright rather than burying it in a privacy policy.
 */
export default function DonorHowItWorks({ compact = false }: { compact?: boolean }) {
  return (
    <section className={`how${compact ? ' how--compact' : ''}`} aria-label="How it works">
      <h2 className="how__title">How it works</h2>
      <ol className="how__steps">
        <li>
          <span className="how__num">1</span>
          <span className="how__text">
            <strong>Find a wish that fits you.</strong> Browse the tree, or let us
            match you on your budget and the things you like to help with.
          </span>
        </li>
        <li>
          <span className="how__num">2</span>
          <span className="how__text">
            <strong>Grant it and drop it off at Yale SOM</strong> during the weekly
            window. You'll get the date, the time and what to bring.
          </span>
        </li>
        <li>
          <span className="how__num">3</span>
          <span className="how__text">
            <strong>We deliver it to your neighbor, and you never see each other's
            personal details.</strong> That's on purpose, to protect each neighbor.
          </span>
        </li>
      </ol>
    </section>
  )
}
