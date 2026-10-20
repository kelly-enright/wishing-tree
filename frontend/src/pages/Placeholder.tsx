import { Link } from 'react-router-dom'

/** Used for anything that is routed but has no screen yet. */
export default function Placeholder({ title, blurb }: { title: string; blurb: string }) {
  return (
    <main className="page">
      <Link to="/" className="page__back">← Wishing Tree</Link>
      <h1 className="page__title">{title}</h1>
      <p className="page__blurb">{blurb}</p>
    </main>
  )
}
