import { Link, Navigate } from 'react-router-dom'
import { clearSession, getSession, type Role } from '../session'

const COPY: Record<Role, { title: string; blurb: string }> = {
  family: {
    title: 'Your wishes',
    blurb:
      'This is where you will chat with the Intake agent, approve each wish before it is submitted, and confirm a delivery window.',
  },
  donor: {
    title: 'Wishes near you',
    blurb:
      'This is where you will browse the wish wall or get matched, grant a wish, and pick a weekly drop-off.',
  },
}

/** A signed-in family or donor screen. The contents arrive in a later problem. */
export default function RoleHome({ role }: { role: Role }) {
  const session = getSession()

  if (!session || session.role !== role) {
    return <Navigate to={role === 'family' ? '/family/signup' : '/donor/signup'} replace />
  }

  const { title, blurb } = COPY[role]

  return (
    <main className="page">
      <Link to="/" className="page__back">← Wishing Tree</Link>

      <p className="signed-in">
        Signed in as <strong>{session.alias}</strong> · {session.zip}
        <button
          type="button"
          className="signed-in__switch"
          onClick={() => {
            clearSession()
            window.location.assign('/')
          }}
        >
          Switch account
        </button>
      </p>

      <h1 className="page__title">{title}</h1>
      <p className="page__blurb">{blurb}</p>
      <p className="page__tag">Coming in a later step of this build.</p>
    </main>
  )
}
