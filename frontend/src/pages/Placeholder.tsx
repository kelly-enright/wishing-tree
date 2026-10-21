import { Link } from 'react-router-dom'
import TopBar from '../components/TopBar'
import Footer from '../components/Footer'

/** Used for anything routed with no screen of its own, including 404. */
export default function Placeholder({ title, blurb }: { title: string; blurb: string }) {
  return (
    <main className="page">
      <TopBar />
      <h1 className="page__title">{title}</h1>
      <p className="page__blurb">{blurb}</p>
      <p className="loginhelp">
        <Link to="/">Back to the start</Link>
      </p>
      <Footer />
    </main>
  )
}
