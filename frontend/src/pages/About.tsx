import { ArrowLeft } from 'lucide-react'
import KellyAndMonty from '../components/KellyAndMonty'
import TopBar, { roleLinks } from '../components/TopBar'
import Footer from '../components/Footer'
import { DriftingLeaves } from '../components/LandingBits'
import { MontySparkles } from '../components/MontySparkles'
import usePageTitle from '../usePageTitle'
import useBodyClass from '../useBodyClass'
import { useSession } from '../session'
import { signOut, switchSide } from '../auth'
import { homePath } from '../session'
import { Link } from 'react-router-dom'

/**
 * About.
 *
 * The text here is Kelly's, word for word. Nothing on this page is written,
 * summarized or embellished by the app — if a claim about her or about
 * Wishing Tree is not in her words below, it is not here.
 */
export default function About() {
  useBodyClass('wt-warm')
  usePageTitle('About')
  const { session, me } = useSession()
  return (
    <main className="page about grain">
      <DriftingLeaves />

      <TopBar
        links={session ? roleLinks(session.role) : undefined}
        alias={session?.alias} me={me}
        onSwitch={signOut} onSwitchSide={switchSide}
      />

      {/* Somewhere to go from here, whether you arrived signed in or not. */}
      <Link className="backlink" to={session ? homePath(session.role) : '/'}>
        <ArrowLeft size={15} aria-hidden="true" />
        {session ? 'Back to Wishing Tree' : 'Back to the start'}
      </Link>

      <section className="about__section about__section--who">
        <h1 className="page__title">Hi, I'm Kelly.</h1>
        <div className="about__who">
          <KellyAndMonty />
          <MontySparkles size={54} />
          <p className="about__para">
            I'm Kelly, an MBA student at Yale School of Management. Before business
            school, I spent nearly a decade building and running operations at a global
            research company and an early-stage startup. Wishing Tree brings those skills
            to something I've cared about for years: making it easier for neighbors to
            help each other.
          </p>
        </div>
      </section>

      <h2 className="about__heading about__heading--why">Why Wishing Tree exists</h2>

      <p className="about__para">
        For seven years, I volunteered at a soup kitchen. Every winter I organized
        clothing drives, collecting scarves, blankets, gloves and coats for the people
        we served. Each year I saw the same thing: so many people who needed help, and
        so many people I knew who wanted to give. There just wasn't a bridge between
        them.
      </p>

      <p className="about__para">
        I saw it again volunteering with Lasagna Love, cooking for families going
        through hard times: a single mom working several jobs, a family spending long
        days at the hospital while their child went through chemo, parents stretching
        every dollar to feed their kids. And I saw it when I tried to help a single
        mother of three who was facing eviction, and realized how hard it was to find a
        simple, trusted way to help someone directly.
      </p>

      <p className="about__para">
        Every December, my church put up a giving tree. Families hung paper ornaments
        with something they needed, and neighbors took an ornament and made the wish
        come true. It worked beautifully, but only once a year. Need doesn't keep a
        calendar.
      </p>

      <p className="about__para about__para--lead">
        Wishing Tree is that bridge: the giving tree, online and all year round, so
        neighbors who want to help can find neighbors who could use it, with everyone's
        privacy protected.
      </p>

      <section className="about__section">
        <h2 className="about__heading">How we protect privacy</h2>
        <p className="about__para">
          Neighbors are never shown by name or address. Wish granters never see who
          they're helping, and neighbors never see who helped them. Every wish is
          checked for personal details before anyone sees it. Gifts are dropped off at
          Yale School of Management, and we deliver them to neighbors ourselves.
        </p>
      </section>



      <p className="about__closing">
        Wishing Tree is starting in New Haven, and I'm the first coordinator, so
        if your wish is granted, I may be the one who brings it to your door.
      </p>

      <Footer />
    </main>
  )
}
