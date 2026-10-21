import { useEffect, useRef, useState } from 'react'
import Monty from './Monty'

/**
 * Monty, pleased — his still face with a small sparkle burst around it.
 *
 * Used at the three moments worth marking: beside the portrait on About, on
 * the wish granter's thank-you screen, and on a wish of theirs that has
 * arrived. About a second, and then only the face is left.
 *
 * The drawing is the content and the sparkle is the decoration, which is why
 * Monty himself never moves: a face that bounces competes with the sentence
 * next to it, and the sentence is what the moment is actually for.
 */

function wantsStillness(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** Seven, around the clock. Each one has its own way out, in `--out-x/y`. */
const SPARKS = [0, 1, 2, 3, 4, 5, 6]

export function MontySparkles({
  size = 72, replay,
}: { size?: number; replay?: string | number }) {
  const [playing, setPlaying] = useState(!wantsStillness())
  const first = useRef(true)

  useEffect(() => {
    if (wantsStillness()) return
    // `replay` changing is what starts it again — a wish id, say. Without it
    // the burst would be stuck finished on a page that stays mounted.
    if (first.current) {
      first.current = false
    } else {
      setPlaying(true)
    }
    const done = setTimeout(() => setPlaying(false), 1200)
    return () => clearTimeout(done)
  }, [replay])

  return (
    <span className={`sparkles${playing ? ' sparkles--go' : ''}`}>
      <Monty size={size} />
      <span className="sparkles__burst" aria-hidden="true">
        {SPARKS.map((i) => (
          <span key={i} className={`sparkles__dot sparkles__dot--${i}`} />
        ))}
      </span>
    </span>
  )
}

export default MontySparkles
