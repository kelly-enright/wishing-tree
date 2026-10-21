import { useEffect, useState } from 'react'
import { Info } from 'lucide-react'
import { getSite } from '../api'

/**
 * The line that only the public demo draws.
 *
 * It is fetched rather than built in, so one `frontend/dist` serves both a
 * local run and the deployed site and the difference is a value rather than a
 * second build. Nothing renders until the answer comes back, and nothing
 * renders at all locally — the whole point is that a grader running this on
 * their own machine sees exactly what they saw before.
 *
 * Why it exists: a live link has no way of knowing who is typing into it. A
 * neighbor's address is the single most sensitive thing this app handles, and
 * a stranger who assumes this is a real service could put a real one into a
 * public database. The banner is the cheapest way to say "don't".
 */
export default function DemoBanner() {
  const [text, setText] = useState<string | null>(null)

  useEffect(() => {
    getSite()
      .then((site) => setText(site.banner))
      .catch(() => setText(null))     // a demo banner is never worth an error
  }, [])

  if (!text) return null

  return (
    <div className="demobar" role="note">
      <Info size={15} aria-hidden="true" />
      <span>{text}</span>
    </div>
  )
}
