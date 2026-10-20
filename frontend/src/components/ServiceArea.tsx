import { useEffect, useState } from 'react'
import { getServiceArea, type ServiceArea as Area } from '../api'

/** The standing notice: where Wishing Tree works today. */
export function ServiceNotice() {
  const [area, setArea] = useState<Area | null>(null)
  useEffect(() => { getServiceArea().then(setArea).catch(() => setArea(null)) }, [])
  if (!area) return null
  return <p className="area-notice">{area.notice}</p>
}

/**
 * The zip field, checked as soon as it is filled in.
 *
 * It is the first thing asked on both sign-ups, so somebody outside the area
 * finds out before typing an address — not after.
 */
export function ZipField({
  value, onChange, onCovered,
}: {
  value: string
  onChange: (zip: string) => void
  onCovered: (covered: boolean | null) => void
}) {
  const [area, setArea] = useState<Area | null>(null)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    if (value.length !== 5) {
      setArea(null)
      onCovered(null)
      return
    }
    setChecking(true)
    let cancelled = false
    getServiceArea(value)
      .then((result) => {
        if (cancelled) return
        setArea(result)
        onCovered(result.covered ?? null)
      })
      .catch(() => { if (!cancelled) { setArea(null); onCovered(null) } })
      .finally(() => { if (!cancelled) setChecking(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return (
    <>
      <label className="field">
        <span className="field__label">Zip code</span>
        <input
          className="field__input" required value={value} inputMode="numeric"
          maxLength={5} placeholder="06511" autoFocus
          onChange={(e) => onChange(e.target.value.replace(/\D/g, '').slice(0, 5))}
        />
        <span className="field__hint">
          We check this first, so you know straight away whether we can reach you.
        </span>
      </label>

      {checking && <p className="area-check area-check--waiting">Checking…</p>}

      {!checking && area?.checked && area.covered && (
        <p className="area-check area-check--yes">{area.message}</p>
      )}

      {!checking && area?.checked && area.covered === false && (
        <div className="area-check area-check--no">
          <p>{area.message}</p>
          <p className="area-check__zips">
            Right now we deliver to {area.zip_codes.join(', ')}.
          </p>
        </div>
      )}
    </>
  )
}
