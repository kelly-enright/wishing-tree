import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { HeartHandshake, Sparkles } from 'lucide-react'
import { useSession } from '../session'
import { switchSide } from '../auth'
import TopBar from '../components/TopBar'
import { PageLoading } from '../components/NeedsSignIn'
import usePageTitle from '../usePageTitle'

/**
 * "Which side are you here for?"
 *
 * Only reached by an email that holds both a neighbor and a wish granter
 * account. Anyone with one account never sees it — login sends them straight
 * on — and anyone with none is sent back to log in.
 */
export default function ChooseSide() {
  usePageTitle('Which side are you here for?')
  const { me, loading } = useSession()
  const navigate = useNavigate()

  const roles = me?.roles ?? []

  useEffect(() => {
    if (loading) return
    if (!me?.signed_in) navigate('/login', { replace: true })
    else if (roles.length === 1) switchSide(roles[0].role)
  }, [loading, me, roles, navigate])

  if (loading || !me?.signed_in) return <PageLoading />

  return (
    <main className="page page--narrow">
      {/* No links: they are signed in, so "Log in" would be nonsense, and
          there is nowhere to go until a side is picked. */}
      <TopBar links={[]} />
      <h1 className="page__title">Which side are you here for?</h1>
      <p className="page__blurb">
        This email has both. You can switch between them any time from the
        account menu.
      </p>

      <div className="sides">
        {roles.map((role) => (
          <button
            key={role.role} type="button" className="sides__card"
            onClick={() => switchSide(role.role)}
          >
            <span className="sides__icon">
              {role.role === 'family'
                ? <Sparkles size={22} aria-hidden="true" />
                : <HeartHandshake size={22} aria-hidden="true" />}
            </span>
            <span className="sides__title">
              {role.role === 'family' ? 'Make a wish' : 'Grant a wish'}
            </span>
            <span className="sides__alias">{role.alias}</span>
          </button>
        ))}
      </div>
    </main>
  )
}
