import Logo from '../components/Logo'
import KellyAndMonty from '../components/KellyAndMonty'

/**
 * About.
 *
 * The text here is Kelly's, word for word. Nothing on this page is written,
 * summarized or embellished by the app — if a claim about her or about
 * Wishing Tree is not in her words below, it is not here.
 */
export default function About() {
  return (
    <main className="page about">
      <header className="page__nav"><Logo size={26} /></header>

      <h1 className="page__title">Why Wishing Tree exists</h1>

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

      <section className="about__section about__section--who">
        <h2 className="about__heading">Who I am</h2>
        <div className="about__who">
          <KellyAndMonty />
          <p className="about__para">
            I'm Kelly, an MBA student at Yale School of Management. Before business
            school, I spent nearly a decade building and running operations at a global
            research company and an early-stage startup. Wishing Tree brings those skills
            to something I've cared about for years: making it easier for neighbors to
            help each other. Wishing Tree is starting in New Haven, and I'm the first
            coordinator, so if your wish is granted, I may be the one who brings it to
            your door.
          </p>
        </div>
      </section>
    </main>
  )
}
