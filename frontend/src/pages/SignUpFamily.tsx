import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatPhone, signUpFamily, userMessage } from '../api'
import HowItWorks from '../components/HowItWorks'
import { ServiceNotice, ZipField } from '../components/ServiceArea'
import { setSession } from '../session'
import FormShell from './FormShell'

export default function SignUpFamily() {
  const [zip, setZip] = useState('')
  const [covered, setCovered] = useState<boolean | null>(null)
  const [address, setAddress] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const family = await signUpFamily({
        zip: zip.trim(),
        contact_address: address.trim(),
        contact_email: email.trim(),
        contact_phone: phone.trim() || null,
      })
      setSession({ role: 'family', alias: family.alias, zip: family.zip })
      navigate('/family')
    } catch (err) {
      setError(userMessage(err, 'We could not create your account just now. Please try again.'))
      setBusy(false)
    }
  }

  return (
    <FormShell
      title="I need help"
      blurb="You get an alias like “Family A59”. That alias is the only name anyone else ever sees."
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
                How the coordinator reaches you about a delivery. We never post it
                and never email you anything else.
              </span>
            </label>

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
              Your address, email and phone are shown only to the Wishing Tree
              coordinator who delivers to you. They are never shown to donors, never
              put on the wish wall, and never sent to the AI.
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
