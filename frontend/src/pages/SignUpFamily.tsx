import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatPhone, signUpFamily, userMessage } from '../api'
import HowItWorks from '../components/HowItWorks'
import { ServiceNotice, ZipField } from '../components/ServiceArea'
import { setMe } from '../session'
import { getMe } from '../api'
import PasswordField from '../components/PasswordField'
import FormShell from './FormShell'
import usePageTitle from '../usePageTitle'

export default function SignUpFamily() {
  usePageTitle('Make a wish')
  const [zip, setZip] = useState('')
  const [covered, setCovered] = useState<boolean | null>(null)
  const [address, setAddress] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signUpFamily({
        zip: zip.trim(),
        contact_address: address.trim(),
        contact_email: email.trim(),
        contact_phone: phone.trim() || null,
        password,
        first_name: firstName.trim() || null,
      })
      setMe(await getMe())
      // Straight to the chat: a brand new neighbor has no wishes to look
      // at, and asking for one is what they came to do. This is the only
      // place that rule applies — "My wishes" always opens "My wishes".
      navigate('/family/new')
    } catch (err) {
      setError(userMessage(err, 'We could not create your account just now. Please try again.'))
      setBusy(false)
    }
  }

  return (
    <FormShell
      title="Make a wish"
      blurb="Everyone needs a hand sometimes. Tell us what would help, and a neighbor nearby can make it happen. You'll only ever appear as “Neighbor A59,” never by name or address."
    >
      <ServiceNotice />
      <HowItWorks compact />

      <form className="form" onSubmit={submit}>
        <ZipField value={zip} onChange={setZip} onCovered={setCovered} />

        {covered !== false && (
          <>
            <label className="field">
              <span className="field__label">Delivery address</span>
              <input
                className="field__input" required={covered === true} value={address}
                placeholder="118 Larkspur St, Apt 3B, New Haven, CT 06511"
                disabled={covered !== true}
                onChange={(e) => setAddress(e.target.value)}
              />
            </label>

            <label className="field">
              <span className="field__label">Email</span>
              <input
                className="field__input" required={covered === true} type="email"
                value={email} placeholder="you@example.com" disabled={covered !== true}
                onChange={(e) => setEmail(e.target.value)}
              />
              <span className="field__hint">
                We'll only use this to coordinate your delivery. It's never shown
                to anyone.
              </span>
            </label>

            <label className="field">
              <span className="field__label">First name <em>(optional)</em></span>
              <input
                className="field__input" value={firstName} disabled={covered !== true}
                placeholder="Dana" maxLength={40} autoComplete="given-name"
                onChange={(e) => setFirstName(e.target.value)}
              />
              <span className="field__hint">
                Only you and our coordinator see this. Neighbors only ever see
                your alias.
              </span>
            </label>

            <PasswordField
              value={password} onChange={setPassword} isNew
              disabled={covered !== true}
              hint="At least 8 characters. A short phrase you'll remember is ideal."
            />

            <label className="field">
              <span className="field__label">Phone <em>(optional)</em></span>
              <input
                className="field__input" value={phone} type="tel"
                placeholder="(203) 555-0104" disabled={covered !== true}
                onChange={(e) => setPhone(formatPhone(e.target.value))}
              />
              <span className="field__hint">
                Only used on delivery day, if the coordinator needs to find your door.
              </span>
            </label>

            <p className="form__privacy">
              Your address, email and phone are only ever seen by the coordinator
              who brings your delivery. They're never shown to the neighbor granting
              your wish, never on the tree, and never sent to the AI.
            </p>
          </>
        )}

        {error && <p className="form__error" role="alert">{error}</p>}

        <button className="btn btn--primary" type="submit" disabled={busy || covered !== true}>
          {busy ? 'Creating…' : 'Create my account'}
        </button>
      </form>
    </FormShell>
  )
}
