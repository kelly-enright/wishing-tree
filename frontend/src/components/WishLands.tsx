import { useEffect, useState } from 'react'

/**
 * A wish joining the tree.
 *
 * One small glowing leaf rises from the foot of the hero, drifts up to the
 * canopy and settles on a branch with a soft sparkle. Three seconds, once a
 * visit, and then it is gone — the leaf fades as the sparkle blooms, so the
 * hero ends exactly as it started. That last part is deliberate: every leaf
 * on this tree is somebody's real wish, and a decorative one left sitting in
 * the canopy would be a wish that nobody made.
 *
 * It lives inside `.hero__tree` rather than in the hero, so "settles onto a
 * branch" is measured against the tree itself and lands in the same place at
 * every width. The journey starts 300px below that, which is the foot of the
 * hero at any size the tree takes.
 *
 * The leaf and the sparkle share one 3s duration and differ only in their
 * keyframes, so the sparkle cannot fire early or late the way a second
 * animation with its own timing would.
 */
export default function WishLands() {
  const [playing, setPlaying] = useState(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false
    try {
      return sessionStorage.getItem('wishingtree.wished') !== 'yes'
    } catch {
      return true
    }
  })

  useEffect(() => {
    if (!playing) return
    try { sessionStorage.setItem('wishingtree.wished', 'yes') } catch { /* off */ }
    const done = setTimeout(() => setPlaying(false), 3100)
    return () => clearTimeout(done)
  }, [playing])

  // Nothing in the DOM once it is over, which is the simplest possible
  // version of "nothing is left behind".
  if (!playing) return null

  return (
    <span className="wishland" aria-hidden="true">
      <span className="wishland__leaf" />
      <span className="wishland__spark" />
    </span>
  )
}
