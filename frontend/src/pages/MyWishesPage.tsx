import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import { getMyWishes, userMessage, type WishProgress } from '../api'
import { useSession } from '../session'
import { signOut, switchSide } from '../auth'
import TopBar, { neighborLinks } from '../components/TopBar'
import NeedsSignIn, { PageLoading } from '../components/NeedsSignIn'
import MyWishes from './MyWishes'
import { MontySays } from '../components/Monty'
import Footer from '../components/Footer'
import usePageTitle from '../usePageTitle'

/**
 * A neighbor's own wishes, and nothing else.
 *
 * This page always shows this page. It used to bounce anybody with no wishes
 * straight to the chat, which meant the "My wishes" tab could not be opened
 * at all until you had one — the tab looked broken rather than empty. Landing
 * on the chat is now something sign-up does once, on the way in.
 *
 * Split from the chat because they answer different questions. This page is
 * "where did my wishes get to?"; the chat is "I want to ask for something".
 * Having both on one scroll meant the tab highlight could never be honest —
 * you were always on both pages at once.
 *
 * Somebody with no wishes yet is sent straight to the chat, because an empty
 * list is not what they came for. They can still reach this page by its tab.
 */
export default function MyWishesPage() {
  usePageTitle('My wishes')
  const { session, me, loading } = useSession()
  const [rows, setRows] = useState<WishProgress[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!session) return
    getMyWishes(session.alias)
      .then((data) => setRows(data.wishes))
      .catch((e) => setError(userMessage(e, 'We could not load your wishes.')))
  }, [session])

  if (loading) return <PageLoading />
  if (!session || session.role !== 'family') return <NeedsSignIn want="family" />

  return (
    <main className="page page--wide">
      <TopBar
        links={neighborLinks('wishes')}
        alias={session.alias} me={me}
        onSwitch={signOut} onSwitchSide={switchSide}
      />

      <div className="wisheshead">
        <h1 className="page__title">
          {me?.first_name ? `Hi, ${me.first_name}` : 'My wishes'}
        </h1>
        <Link className="btn btn--primary" to="/family/new">
          <Plus size={16} aria-hidden="true" />
          Make a new wish
        </Link>
      </div>

      {error && <p className="form__error">{error}</p>}

      {rows?.length === 0 ? (
        <div className="emptywishes">
          <MontySays mood="calm">
            <strong>No wishes yet.</strong><br />
            When you make a wish, it'll show up here with where it has got to.
          </MontySays>
          <Link className="btn btn--primary" to="/family/new">
            <Plus size={16} aria-hidden="true" />
            Make a new wish
          </Link>
        </div>
      ) : (
        <MyWishes alias={session.alias} />
      )}

      <Footer />
    </main>
  )
}
