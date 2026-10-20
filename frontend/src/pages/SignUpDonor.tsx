import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CATEGORY_LABELS, signUpDonor, type Category, type Preference } from '../api'
import { setSession } from '../session'
import FormShell from './FormShell'

const PREFERENCES: { value: Preference; label: string }[] = [
  { value: 'specific', label: 'Specific items — an exact thing to buy' },
  { value: 'flexible', label: 'Flexible needs — I will choose something that fits' },
  { value: 'either', label: 'Either is fine' },
]

export default function SignUpDonor() {
  const [zip, setZip] = useState('')
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
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
      const donor = await signUpDonor({
        zip: zip.trim(),
        contact_address: address.trim(),
        contact_phone: phone.trim(),
        budget_usd: Number(budget) || 0,
        preferred_categories: categories,
        preference,
      })
      setSession({ role: 'donor', alias: donor.alias, zip: donor.zip })
      navigate('/donor')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setBusy(false)
    }
  }

  return (
    <FormShell
      title="I want to give"
      blurb="Tell us where you are and what you like to help with. You get an alias like “Donor D09”."
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
          <span className="field__label">Address</span>
          <input
            className="field__input" required value={address}
            placeholder="88 Elmcrest Ter, New Haven, CT 06511"
            onChange={(e) => setAddress(e.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Phone</span>
          <input
            className="field__input" required value={phone} type="tel"
            placeholder="(203) 555-0201" onChange={(e) => setPhone(e.target.value)}
          />
        </label>

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
          Your address and phone are shown only to the coordinator. Families never see them.
        </p>

        {error && <p className="form__error" role="alert">{error}</p>}

        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? 'Creating…' : 'Create my account'}
        </button>
      </form>
    </FormShell>
  )
}
