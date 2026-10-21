import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

/**
 * A box that explains something, open the first time and folded away after.
 *
 * "How it works" earns its space on a first visit and stops earning it on the
 * fifth. The choice is remembered per browser under `id`, so someone who
 * folds it keeps it folded, and someone who never touches it keeps it open.
 *
 * Reading localStorage during the first render rather than in an effect
 * matters: an effect would show the box open for a frame before snapping it
 * shut, which looks like a bug.
 */
export default function Collapsible({
  id, title, children, defaultOpen = true,
}: {
  id: string; title: string; children: React.ReactNode
  /** False where the box is a line to tap rather than something to read —
   *  on a phone, above a tree that wants the screen. */
  defaultOpen?: boolean
}) {
  const key = `wishingtree.${id}.folded`
  const [open, setOpen] = useState(() => {
    try {
      const saved = localStorage.getItem(key)
      return saved === null ? defaultOpen : saved !== 'yes'
    } catch {
      return defaultOpen
    }
  })

  function toggle() {
    setOpen((was) => {
      try {
        localStorage.setItem(key, was ? 'yes' : 'no')
      } catch { /* a browser with storage off still gets a working toggle */ }
      return !was
    })
  }

  return (
    <section className={`fold${open ? ' fold--open' : ''}`}>
      <button
        type="button" className="fold__head" aria-expanded={open} onClick={toggle}
      >
        <span className="fold__title">{title}</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {open && <div className="fold__body">{children}</div>}
    </section>
  )
}
