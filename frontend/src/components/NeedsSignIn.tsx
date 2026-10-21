import { Link } from 'react-router-dom'
import TopBar from './TopBar'
import { SkeletonRows } from './Skeleton'

/**
 * What a page shows when nobody is signed in, and while it is still asking.
 *
 * Both have navigation, because a dead end is the thing this problem set out
 * to remove: whatever brought someone here, there is a way on from it.
 */

export function PageLoading() {
  return (
    <main className="page">
      <TopBar />
      <p className="sr-only" role="status">Loading…</p>
      <SkeletonRows count={2} />
    </main>
  )
}

export default function NeedsSignIn({ want }: { want: 'family' | 'donor' }) {
  const making = want === 'family'
  return (
    <main className="page">
      <TopBar />
      <h1 className="page__title">{making ? 'Make a wish' : 'Grant a wish'}</h1>
      <p className="page__blurb">
        {making
          ? 'Log in to see your wishes, or create an account and tell us what would help.'
          : 'Log in to see the tree, or create an account to start granting wishes.'}
      </p>
      <div className="review__actions">
        <Link className="btn btn--primary" to="/login">Log in</Link>
        <Link className="btn btn--light" to={making ? '/family/signup' : '/donor/signup'}>
          Create account
        </Link>
      </div>
    </main>
  )
}
