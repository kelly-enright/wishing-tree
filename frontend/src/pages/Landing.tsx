import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  demoLogIn, getStats, getWishes, listAccounts,
  type Account, type Stats, type WallFilters, type WishWall, type WishCard as Wish,
  userMessage,
} from '../api'
import Monty from '../components/Monty'
import TopBar from '../components/TopBar'
import useBodyClass from '../useBodyClass'
import WishTree from '../components/WishTree'
import WishCard from '../components/WishCard'
import {
  CategoryRange, CountUp, DriftingLeaves, Hills, Reveal, ThreeSteps,
} from '../components/LandingBits'
import WishLands from '../components/WishLands'
import Footer from '../components/Footer'
import { ServiceNotice } from '../components/ServiceArea'
import { homePath, setMe, useSession } from '../session'
import { signOut, switchSide } from '../auth'

// Two doors, because almost everyone arriving is here for one of them.
// Admin is a handful of staff and lives in the footer, where it is still one
// click away without competing with the reason anyone else came.
const ROLES = [
  {
    to: '/family/signup',
    eyebrow: 'If you could use a hand',
    title: 'Make a wish',
    blurb: 'Something you or your family could use? Ask your neighbors.',
  },
  {
    to: '/donor/signup',
    eyebrow: "If you'd like to help",
    title: 'Grant a wish',
    blurb: 'Help a neighbor with something they need.',
  },
]

const EMPTY_FILTERS: WallFilters = {
  categories: [], occasion: '', requestType: '', maxCost: '',
}

export default function Landing() {
  useBodyClass('wt-warm')
  const [stats, setStats] = useState<Stats | null>(null)
  const [accounts, setAccounts] = useState<{ families: Account[]; donors: Account[] } | null>(null)
  const [showAccounts, setShowAccounts] = useState(false)
  const { session, me } = useSession()
  const [demoError, setDemoError] = useState<string | null>(null)
  const [tree, setTree] = useState<WishWall | null>(null)
  // The oldest open wish, so the example is a real one and does not change
  // under somebody between two page loads.
  const example = tree?.wishes.length
    ? [...tree.wishes].sort((a, b) => b.days_waiting - a.days_waiting)[0]
    : null
  const navigate = useNavigate()

  useEffect(() => { getStats().then(setStats).catch(() => setStats(null)) }, [])

  // The real tree, as it is right now. Public data — it is the same list a
  // signed-in granter sees — so a visitor gets the truth, not a mock-up.
  useEffect(() => { getWishes(EMPTY_FILTERS).then(setTree).catch(() => setTree(null)) }, [])

  /**
   * Tapping a leaf and then "Grant this wish" when signed out.
   *
   * The wish is carried through sign-in in the URL and handed back on the
   * other side, so someone who came for one particular wish lands on that
   * wish rather than on a tree of thirty and the job of finding it again.
   */
  function grantAfterSignIn(wish: Wish) {
    const back = `/donor?wish=${wish.id}`
    navigate(`/login?next=${encodeURIComponent(back)}`)
  }


  useEffect(() => {
    if (!showAccounts || accounts) return
    listAccounts().then(setAccounts).catch(() => setAccounts({ families: [], donors: [] }))
  }, [showAccounts, accounts])

  /**
   * The demo shortcut, which now logs in for real.
   *
   * Every seeded account has a published password, so this goes through the
   * same login as anyone else rather than round the back of it. That keeps
   * the shortcut honest: what it demonstrates is the app, not a bypass.
   */
  async function continueAs(account: Account) {
    setDemoError(null)
    try {
      const signedIn = await demoLogIn(account.alias)
      setMe(signedIn)
      if (signedIn.must_choose) {
        await switchSide(account.role)
      } else {
        navigate(homePath(account.role))
      }
    } catch (err) {
      setDemoError(userMessage(err, 'That demo account could not be opened.'))
    }
  }

  return (
    <main className="landing grain">
      <TopBar
        alias={session?.alias} me={me}
        onSwitch={signOut} onSwitchSide={switchSide}
      />

      <header className="hero">
        <h1 className="hero__tagline">Grant a neighbor's wish, any time of year</h1>

        {/* The counter and the service area say the same kind of thing — this
            is real, and it is here — so they say it together, once. */}
        {stats && stats.wishes_granted > 0 ? (
          <div className="tally">
            <strong className="tally__number">
              <CountUp to={stats.wishes_granted} />
            </strong>
            <div>
              <p className="tally__line">
                wish{stats.wishes_granted === 1 ? '' : 'es'} granted so far
              </p>
              <p className="tally__where">{stats.line}</p>
              <ServiceNotice />
            </div>
          </div>
        ) : (
          <ServiceNotice />
        )}

        {tree && tree.wishes.length > 0 && (
          <div className="hero__tree">
            <WishLands />
            <WishTree
              hills={<Hills />}
              wishes={tree.wishes}
              granted={tree.recently_granted}
              grantedWindowDays={tree.granted_window_days}
              onGrant={grantAfterSignIn}
              granting={null}
              onSeeList={() => navigate('/how-it-works')}
              compact
              swaying
              grantLabel="Grant this wish"
            />
          </div>
        )}

        <div className="hero__monty">
          <Monty size={96} />
          <p className="hero__pick">
            Monty here. Pick the one that sounds like you.{' '}
            <Link className="hero__about" to="/about">Why we exist</Link>
          </p>
        </div>
      </header>

      {session && (
        <section className="welcome" aria-label="Signed in">
          <p className="welcome__text">
            This browser is signed in as <strong>{session.alias}</strong>.
          </p>
          <div className="welcome__actions">
            <Link className="btn btn--light" to={homePath(session.role)}>
              Continue
            </Link>
            <button type="button" className="btn btn--ghost" onClick={signOut}>
              Sign out
            </button>
          </div>
        </section>
      )}

      <DriftingLeaves />

      <section className="roles" aria-label="Choose how you want to start">
        {ROLES.map((role) => (
          <Link key={role.to} to={role.to} className="role">
            <span className="role__eyebrow">{role.eyebrow}</span>
            <span className="role__title">{role.title}</span>
            <span className="role__blurb">{role.blurb}</span>
            <span className="role__go" aria-hidden="true">Start here →</span>
          </Link>
        ))}
      </section>

      <section className="band band--sage" aria-label="How it works">
        <h2 className="band__title">How it works</h2>
        <ThreeSteps />
      </section>

      {example && (
        <section className="band" aria-label="An example wish">
          <Reveal>
            <h2 className="band__title">Here's what a wish looks like</h2>
            <p className="band__blurb">
              A real one, on the tree right now. No name, no address — nothing
              that points back to the neighbor who asked.
            </p>
            <div className="band__card">
              <WishCard wish={example} />
            </div>
          </Reveal>
        </section>
      )}

      <section className="band" aria-label="The range of wishes">
        <Reveal>
          <h2 className="band__title">Wishes of every kind</h2>
          <CategoryRange />
        </Reveal>
      </section>

      <section className="demo" aria-label="Demo shortcut">
        <div className="demo__header">
          <div>
            <p className="demo__tag">Demo shortcut — not part of the real product</p>
            <p className="demo__text">
              Continue as an existing neighbor or wish granter, without signing up.
            </p>
          </div>
          <button
            type="button"
            className="btn btn--light"
            onClick={() => setShowAccounts((open) => !open)}
            aria-expanded={showAccounts}
          >
            {showAccounts ? 'Hide accounts' : 'Continue as…'}
          </button>
        </div>

        {demoError && <p className="form__error" role="alert">{demoError}</p>}

        {showAccounts && (
          <div className="accounts">
            {!accounts && <p className="accounts__loading">Loading accounts…</p>}
            {accounts && accounts.families.length === 0 && accounts.donors.length === 0 && (
              <p className="accounts__loading">
                No demo accounts yet — sign up above and you'll appear here.
              </p>
            )}
            {accounts && (
              <>
                <div className="accounts__group">
                  <h2 className="accounts__title">Making a wish</h2>
                  <ul className="accounts__list">
                    {accounts.families.map((account) => (
                      <li key={account.alias}>
                        <button type="button" className="account" onClick={() => continueAs(account)}>
                          <span className="account__alias">{account.alias}</span>
                          <span className="account__detail">
                            {account.zip} · {account.detail}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="accounts__group">
                  <h2 className="accounts__title">Granting a wish</h2>
                  <ul className="accounts__list">
                    {accounts.donors.map((account) => (
                      <li key={account.alias}>
                        <button type="button" className="account" onClick={() => continueAs(account)}>
                          <span className="account__alias">{account.alias}</span>
                          <span className="account__detail">
                            {account.zip} · {account.detail}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        )}
      </section>

      <Footer />
    </main>
  )
}
