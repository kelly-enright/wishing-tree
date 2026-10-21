import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CATEGORY_LABELS, formatPhone, signUpDonor, type Category, type Preference,
  userMessage,
} from '../api'
import { ServiceNotice, ZipField } from '../components/ServiceArea'
import { setMe } from '../session'
import { getMe } from '../api'
import PasswordField from '../components/PasswordField'
import FormShell from './FormShell'
import usePageTitle from '../usePageTitle'

const PREFERENCES: { value: Preference; label: string }[] = [
  { value: 'specific', label: 'Specific items — an exact thing to buy' },
  { value: 'flexible', label: 'Flexible needs — I will choose something that fits' },
  { value: 'either', label: 'Either is fine' },
]

export default function SignUpDonor() {
  usePageTitle('Grant a wish')
  const [zip, setZip] = useState('')
  const [covered, setCovered] = useState<boolean | null>(null)
  const [email, setEmail] = useState('')
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [budget, setBudget] = useState('75')
  const [categories, setCategories] = useState<Category[]>([])
  const [preference, setPreference] = useState<Preference>('either')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  function toggle(category: Category) {
    setCategories((current) =>
      current.includes(category)
        ? current.filter((c) => c !== category)
        : [...current, category],
    )
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signUpDonor({
        zip: zip.trim(),
        contact_address: address.trim(),
        contact_email: email.trim(),
        contact_phone: phone.trim() || null,
        password,
        first_name: firstName.trim() || null,
        budget_usd: Number(budget) || 0,
        preferred_categories: categories,
        preference,
      })
      setMe(await getMe())
      navigate('/donor')
    } catch (err) {
      setError(userMessage(err, 'We could not create your account just now. Please try again.'))
      setBusy(false)
    }
  }

  return (
    <FormShell
      title="Grant a wish"
      blurb="Tell us where you are and what you like to help with. You'll appear as “Granter D09” — a neighbor never sees your name."
    >
      <ServiceNotice />

      <form className="form" onSubmit={submit}>
        <ZipField value={zip} onChange={setZip} onCovered={setCovered} />

        <label className="field">
          <span className="field__label">Address</span>
          <input
            className="field__input" required value={address}
            placeholder="88 Elmcrest Ter, New Haven, CT 06511"
            onChange={(e) => setAddress(e.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Email</span>
          <input
            className="field__input" required type="email" value={email}
            placeholder="you@example.com" onChange={(e) => setEmail(e.target.value)}
          />
          <span className="field__hint">
            We'll only use this to coordinate your drop-off. It's never shown to
            the neighbor whose wish you grant.
          </span>
        </label>

        <label className="field">
          <span className="field__label">Phone <em>(optional)</em></span>
          <input
            className="field__input" value={phone} type="tel"
            placeholder="(203) 555-0201"
            onChange={(e) => setPhone(formatPhone(e.target.value))}
          />
          <span className="field__hint">Only used on drop-off day.</span>
        </label>

        <label className="field">
          <span className="field__label">First name <em>(optional)</em></span>
          <input
            className="field__input" value={firstName} disabled={covered !== true}
            placeholder="Theo" maxLength={40} autoComplete="given-name"
            onChange={(e) => setFirstName(e.target.value)}
          />
          <span className="field__hint">
            Only you and our coordinator see this. The neighbor whose wish you
            grant only ever sees your alias.
          </span>
        </label>

        <PasswordField
          value={password} onChange={setPassword} isNew
          disabled={covered !== true}
          hint="At least 8 characters. A short phrase you'll remember is ideal."
        />

        <label className="field">
          <span className="field__label">Budget per wish (USD)</span>
          <input
            className="field__input" required value={budget} type="number" min="0" step="5"
            onChange={(e) => setBudget(e.target.value)}
          />
        </label>

        <fieldset className="fieldset">
          <legend className="field__label">Categories you like to help with</legend>
          <div className="checks">
            {(Object.keys(CATEGORY_LABELS) as Category[]).map((category) => (
              <label key={category} className="check">
                <input
                  type="checkbox"
                  checked={categories.includes(category)}
                  onChange={() => toggle(category)}
                />
                <span>{CATEGORY_LABELS[category]}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="fieldset">
          <legend className="field__label">What do you prefer to grant?</legend>
          <div className="checks">
            {PREFERENCES.map((option) => (
              <label key={option.value} className="check">
                <input
                  type="radio" name="preference" value={option.value}
                  checked={preference === option.value}
                  onChange={() => setPreference(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <p className="form__privacy">
          Your address, email and phone are only ever seen by the coordinator.
          You won't see a neighbor's name or address, and they won't see yours.
          That's on purpose, to protect each neighbor.
        </p>

        {error && <p className="form__error" role="alert">{error}</p>}

        <button className="btn btn--primary" type="submit" disabled={busy || covered !== true}>
          {busy ? 'Creating…' : 'Create my account'}
        </button>
      </form>
    </FormShell>
  )
}
