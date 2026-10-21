import { useEffect, useRef, useState } from 'react'
import Monty from './Monty'
import MontyBody from './MontyBody'

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

/** The pile he lands in. Six leaves, each with its own direction out. */
function LeafPile() {
  return (
    <span className="pile" aria-hidden="true">
      {/* A heap for the loose leaves to sit on, so it reads as a pile he is
          in rather than leaves lying near him. */}
      <span className="pile__mound" />
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={`pile__leaf pile__leaf--${i}`} />
      ))}
    </span>
  )
}

/**
 * The landing page welcome: trot in, leap, land in the leaves, look up.
 *
 * Four and a half seconds, once a visit. "Once" is held in `sessionStorage`
 * rather than state — a visitor who goes to About and comes back should not
 * be greeted again, and a React remount would otherwise replay it.
 *
 * What is on screen afterwards is the point of the structure: the dog's
 * *resting* CSS position is where he ends up, sitting in the pile with the
 * leaves drawn in front of him, and the animation travels him in from off
 * the left. So when the animation does not run at all — reduced motion, or
 * a second visit — the page shows him already peeking out of the finished
 * pile, which is exactly the still version that was asked for. Nothing is
 * left floating, because nothing was ever positioned for the journey.
 */
export function MontyArrives() {
  const [playing, setPlaying] = useState(() =>
    !wantsStillness() && sessionStorage.getItem('wishingtree.greeted') !== 'yes',
  )

  useEffect(() => {
    if (!playing) return
    try { sessionStorage.setItem('wishingtree.greeted', 'yes') } catch { /* off */ }
    const done = setTimeout(() => setPlaying(false), 4800)
    return () => clearTimeout(done)
  }, [playing])

  return (
    <div className={`arrival${playing ? ' arrival--go' : ''}`} aria-hidden="true">
      <span className="arrival__dog"><MontyBody size={76} /></span>
      <LeafPile />
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
      <LeafPile />
      <span className="plays__monty"><Monty size={size} /></span>
    </span>
  )
}
