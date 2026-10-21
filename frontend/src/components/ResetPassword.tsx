import { useState } from 'react'
import { KeyRound } from 'lucide-react'
import { issueResetCode, userMessage } from '../api'

/**
 * The coordinator's "Reset password" control, beside a person on the run sheet.
 *
 * No email is sent, because Wishing Tree sends none. This issues a one-time
 * code to read out or hand over, and that is all a coordinator ever holds:
 * the person sets their own password with it. Staff never see or choose a
 * password, which is why the button says Reset rather than Set.
 */
export default function ResetPassword({ token, alias }: { token: string; alias: string }) {
  const [code, setCode] = useState<string | null>(null)
  const [how, setHow] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function issue() {
    setBusy(true)
    setError(null)
    try {
      const result = await issueResetCode(token, alias)
      setCode(result.code)
      setHow(result.how)
    } catch (err) {
      setError(userMessage(err, 'We could not issue a code just now.'))
    } finally {
      setBusy(false)
    }
  }

  if (code) {
    return (
      <div className="resetcode">
        <p className="resetcode__code">{code}</p>
        <p className="resetcode__how">{how}</p>
      </div>
    )
  }

  return (
    <>
      <button
        type="button" className="btn btn--light btn--small"
        disabled={busy} onClick={issue}
      >
        <KeyRound size={13} aria-hidden="true" />
        {busy ? 'Issuing…' : 'Reset password'}
      </button>
      {error && <p className="form__error" role="alert">{error}</p>}
    </>
  )
}
