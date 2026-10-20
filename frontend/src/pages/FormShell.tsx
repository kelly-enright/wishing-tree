import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

/** Shared chrome for the sign-up and passcode screens. */
export default function FormShell({
  title,
  blurb,
  children,
}: {
  title: string
  blurb: string
  children: ReactNode
}) {
  return (
    <main className="page">
      <Link to="/" className="page__back">← Wishing Tree</Link>
      <h1 className="page__title">{title}</h1>
      <p className="page__blurb">{blurb}</p>
      {children}
    </main>
  )
}
