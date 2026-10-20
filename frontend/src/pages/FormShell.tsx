import type { ReactNode } from 'react'
import Logo from '../components/Logo'

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
      <header className="page__nav"><Logo size={26} /></header>
      <h1 className="page__title">{title}</h1>
      <p className="page__blurb">{blurb}</p>
      {children}
    </main>
  )
}
