import { useEffect, useRef, useState } from 'react'
import Monty from './Monty'

/**
 * Monty, animated — twice, in two different ways.
 *
 * `MontyArrives` is the landing page's welcome: he trots along under the
 * header, bounds through a pile of leaves, and settles beside the logo.
 * `MontyInLeaves` is the shorter one used at three moments worth marking.
 *
 * Both are CSS animations on `transform` and `opacity` only, so they run on
 * the compositor and cost nothing while they play. Both run once and stop —
 * `animation-fill-mode: both` holds the last frame rather than snapping back
 * — and both are replaced by a still Monty under reduced motion, which is
 * the point: the drawing is the content, the movement is decoration.
 */

function wantsStillness(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** A small scatter of leaves for him to bound through. */
function LeafPile({ puffing }: { puffing: boolean }) {
  return (
    <span className={`pile${puffing ? ' pile--puff' : ''}`} aria-hidden="true">
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`pile__leaf pile__leaf--${i}`} />
      ))}
    </span>
  )
}

/**
 * The landing page welcome. Roughly three and a half seconds, once a visit.
 *
 * "Once a visit" is held in `sessionStorage`, not state: a visitor who goes
 * to About and comes back should not be greeted all over again, and a React
 * remount would otherwise replay it.
 */
export function MontyArrives() {
  const [phase, setPhase] = useState<'waiting' | 'running' | 'done'>(() =>
    wantsStillness() || sessionStorage.getItem('wishingtree.greeted') === 'yes'
      ? 'done'
      : 'waiting',
  )

  useEffect(() => {
    if (phase !== 'waiting') return
    try { sessionStorage.setItem('wishingtree.greeted', 'yes') } catch { /* off */ }
    const start = setTimeout(() => setPhase('running'), 240)
    const end = setTimeout(() => setPhase('done'), 3800)
    return () => { clearTimeout(start); clearTimeout(end) }
  }, [phase])

  if (phase === 'done') return null

  return (
    <div
      className={`arrive${phase === 'running' ? ' arrive--go' : ''}`}
      aria-hidden="true"
    >
      <LeafPile puffing={phase === 'running'} />
      <span className="arrive__monty">
        <Monty size={46} />
      </span>
    </div>
  )
}

/**
 * Monty having a moment in the leaves. Two and a half seconds, then still.
 *
 * `replay` is a value that, when it changes, starts it again — a wish id,
 * say. Without it the animation would be stuck finished after the first use
 * on a page that stays mounted.
 */
export function MontyInLeaves({
  size = 72, replay,
}: { size?: number; replay?: string | number }) {
  const [playing, setPlaying] = useState(!wantsStillness())
  const first = useRef(true)

  useEffect(() => {
    if (wantsStillness()) return
    if (first.current) {
      first.current = false
    } else {
      setPlaying(true)
    }
    const done = setTimeout(() => setPlaying(false), 2600)
    return () => clearTimeout(done)
  }, [replay])

  return (
    <span className={`plays${playing ? ' plays--go' : ''}`} aria-hidden="true">
      <LeafPile puffing={playing} />
      <span className="plays__monty"><Monty size={size} /></span>
    </span>
  )
}
