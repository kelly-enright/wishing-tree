import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import type { WishCard as Wish } from '../api'
import WishCard from './WishCard'

/**
 * A wish, opened where the person is already looking.
 *
 * Two presentations of the same thing. On a wide screen the wish takes over
 * the panel beside the tree, so the tree does not move and the leaf they
 * tapped stays where their eye is. On a phone there is no beside, so it
 * comes up as a sheet over the tree.
 *
 * Both close on Escape and on a click outside, and both hand focus back to
 * the leaf that opened them — a keyboard user who closes a wish should be on
 * the leaf they came from, not at the top of the page.
 */

/** True while the viewport is at or under `maxWidth`. */
export function useNarrow(maxWidth = 900): boolean {
  const [narrow, setNarrow] = useState(
    () => window.matchMedia(`(max-width: ${maxWidth}px)`).matches,
  )
  useEffect(() => {
    const query = window.matchMedia(`(max-width: ${maxWidth}px)`)
    const sync = () => setNarrow(query.matches)
    query.addEventListener('change', sync)
    return () => query.removeEventListener('change', sync)
  }, [maxWidth])
  return narrow
}

/** The id the tree gives each leaf, so focus can go back to the right one. */
export function leafId(wishId: number): string {
  return `leaf-${wishId}`
}

function returnFocusTo(wishId: number) {
  document.getElementById(leafId(wishId))?.focus()
}

/**
 * Escape, and a click outside. Shared by both presentations.
 *
 * `pointerdown` rather than `click`, so a tap that starts outside closes even
 * if the finger drifts. A leaf is "outside" on purpose: tapping a different
 * leaf closes this wish and opens that one in the same gesture, which is what
 * it looks like it should do.
 */
function useDismiss(
  box: React.RefObject<HTMLElement | null>, onClose: () => void,
) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    function onOutside(event: PointerEvent) {
      if (!box.current?.contains(event.target as Node)) onClose()
    }
    document.addEventListener('keydown', onKey)
    // Deferred a tick: the click that opened this would otherwise close it
    // again on the way back up.
    const armed = setTimeout(
      () => document.addEventListener('pointerdown', onOutside), 0)
    return () => {
      clearTimeout(armed)
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onOutside)
    }
  }, [box, onClose])
}

type Props = {
  wish: Wish
  onGrant: (wish: Wish) => void
  granting: boolean
  grantLabel?: string
  reason?: string
  onClose: () => void
}

/** The wide version: the wish takes the panel beside the tree. */
export function WishPanel({ wish, onGrant, granting, grantLabel, reason, onClose }: Props) {
  const box = useRef<HTMLDivElement>(null)
  useDismiss(box, onClose)

  useEffect(() => {
    box.current?.focus()
  }, [wish.id])

  function close() {
    returnFocusTo(wish.id)
    onClose()
  }

  return (
    <div
      className="wishpanel" ref={box} tabIndex={-1}
      aria-label={`Wish: ${wish.item_description}`}
    >
      <button
        type="button" className="wishpanel__close" onClick={close}
        aria-label="Close this wish"
      >
        <X size={16} aria-hidden="true" />
      </button>
      <WishCard
        wish={wish} reason={reason} onGrant={onGrant}
        granting={granting} grantLabel={grantLabel}
      />
    </div>
  )
}

/**
 * The narrow version: a sheet over the tree.
 *
 * Modal, because it covers what is behind it — so Tab is kept inside it while
 * it is open, rather than wandering off into a tree nobody can see.
 */
export function WishSheet({ wish, onGrant, granting, grantLabel, reason, onClose }: Props) {
  const box = useRef<HTMLDivElement>(null)
  useDismiss(box, onClose)

  useEffect(() => {
    box.current?.focus()
  }, [wish.id])

  useEffect(() => {
    function trap(event: KeyboardEvent) {
      if (event.key !== 'Tab' || !box.current) return
      const stops = box.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
      if (stops.length === 0) return
      const first = stops[0]
      const last = stops[stops.length - 1]
      const on = document.activeElement
      if (event.shiftKey && (on === first || on === box.current)) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && on === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', trap)
    return () => document.removeEventListener('keydown', trap)
  }, [])

  function close() {
    returnFocusTo(wish.id)
    onClose()
  }

  return (
    <div className="sheetwrap layer">
      <div className="sheetwrap__scrim" aria-hidden="true" />
      <div
        className="wishsheet" ref={box} tabIndex={-1}
        role="dialog" aria-modal="true"
        aria-label={`Wish: ${wish.item_description}`}
      >
        <div className="wishsheet__grip" aria-hidden="true" />
        <button
          type="button" className="wishsheet__close" onClick={close}
        >
          <X size={15} aria-hidden="true" />
          Close
        </button>
        <WishCard
          wish={wish} reason={reason} onGrant={onGrant}
          granting={granting} grantLabel={grantLabel}
        />
      </div>
    </div>
  )
}

/**
 * Whichever of the two fits the screen. Callers hold the open wish and say
 * what granting it does; this decides how it is shown.
 */
export default function WishOpen(props: Props & { always?: 'sheet' }) {
  const narrow = useNarrow(900)
  const { always, ...rest } = props
  return narrow || always === 'sheet' ? <WishSheet {...rest} /> : <WishPanel {...rest} />
}
