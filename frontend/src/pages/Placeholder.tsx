import { Link } from 'react-router-dom'

/** A screen that is routed and styled, but whose contents arrive in a later problem. */
export default function Placeholder({ title, blurb }: { title: string; blurb: string }) {
  return (
    <main className="placeholder">
      <Link to="/" className="placeholder__back">← Wishing Tree</Link>
      <h1 className="placeholder__title">{title}</h1>
      <p className="placeholder__blurb">{blurb}</p>
      <p className="placeholder__tag">Coming in a later step of this build.</p>
    </main>
  )
}
