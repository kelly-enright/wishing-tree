import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

/**
 * One password field, with a show/hide control.
 *
 * Typing a password you cannot see, on a phone, is how people end up choosing
 * short ones. Showing it on request is the small kindness that lets somebody
 * use a long phrase instead — and the same control the admin passcode screen
 * already has, so it behaves the way the rest of the app does.
 *
 * `autoComplete` is set deliberately: a password manager that knows this is a
 * new password offers to generate one, and one that knows it is a returning
 * password fills it.
 */
export default function PasswordField({
  value, onChange, label = 'Password', isNew = false, hint, disabled = false,
}: {
  value: string
  onChange: (value: string) => void
  label?: string
  isNew?: boolean
  hint?: string
  disabled?: boolean
}) {
  const [shown, setShown] = useState(false)
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      <span className="field__reveal">
        <input
          className="field__input"
          type={shown ? 'text' : 'password'}
          value={value} required disabled={disabled}
          minLength={isNew ? 8 : undefined}
          autoComplete={isNew ? 'new-password' : 'current-password'}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button" className="field__eye"
          aria-label={shown ? 'Hide password' : 'Show password'}
          aria-pressed={shown}
          onClick={() => setShown((on) => !on)}
        >
          {shown ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </span>
      {hint && <span className="field__hint">{hint}</span>}
    </label>
  )
}
