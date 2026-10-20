import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { signUpFamily } from '../api'
import { setSession } from '../session'
import FormShell from './FormShell'

export default function SignUpFamily() {
  const [zip, setZip] = useState('')
  const [address, setAddress] = useState('')
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
        contact_phone: phone.trim(),
      })
      setSession({ role: 'family', alias: family.alias, zip: family.zip })
      navigate('/family')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setBusy(false)
    }
  }

  return (
    <FormShell
      title="I need help"
      blurb="You get an alias like “Family A59”. That alias is the only name anyone else ever sees."
    >
      <form className="form" onSubmit={submit}>
        <label className="field">
          <span className="field__label">Zip code</span>
          <input
            className="field__input" required value={zip} inputMode="numeric"
            maxLength={5} placeholder="06511" onChange={(e) => setZip(e.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Delivery address</span>
          <input
            className="field__input" required value={address}
            placeholder="118 Larkspur St, Apt 3B, New Haven, CT 06511"
            onChange={(e) => setAddress(e.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Phone</span>
          <input
            className="field__input" required value={phone} type="tel"
            placeholder="(203) 555-0104" onChange={(e) => setPhone(e.target.value)}
          />
        </label>

        <p className="form__privacy">
          Your address and phone are shown only to the Wishing Tree coordinator who
          delivers to you. They are never shown to donors, never put on the wish wall,
          and never sent to the AI.
        </p>

        {error && <p className="form__error" role="alert">{error}</p>}

        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? 'Creating…' : 'Create my account'}
        </button>
      </form>
    </FormShell>
  )
}
