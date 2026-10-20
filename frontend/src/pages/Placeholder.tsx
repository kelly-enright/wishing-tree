import Logo from '../components/Logo'

/** Used for anything that is routed but has no screen yet. */
export default function Placeholder({ title, blurb }: { title: string; blurb: string }) {
  return (
    <main className="page">
      <header className="page__nav"><Logo size={26} /></header>
      <h1 className="page__title">{title}</h1>
      <p className="page__blurb">{blurb}</p>
    </main>
  )
}
