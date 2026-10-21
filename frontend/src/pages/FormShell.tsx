import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import TopBar from '../components/TopBar'
import Footer from '../components/Footer'

/**
 * Shared chrome for the sign-up screens.
 *
 * The navigation and the footer live here rather than in each form, so a
 * half-finished sign-up is never a dead end: there is always a way to the
 * other side of the app, to How it works, or to log in instead.
 */
export default function FormShell({
  title,
  blurb,
  children,
  footnote,
}: {
  title: string
  blurb: string
  children: ReactNode
  footnote?: ReactNode
}) {
  return (
    <main className="page page--narrow">
      <TopBar />
      <h1 className="page__title">{title}</h1>
      <p className="page__blurb">{blurb}</p>
      {children}
      <p className="loginhelp">
        {footnote ?? <>Already have an account? <Link to="/login">Log in</Link>.</>}
      </p>
      <Footer />
    </main>
  )
}
