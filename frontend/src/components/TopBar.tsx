import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import Logo from './Logo'

/**
 * The slim bar at the top of every signed-in screen.
 *
 * Pinned, because the links are how you move between the two halves of your
 * own side of the app, and hunting for them at the top of a long tree is the
 * kind of small friction that makes software feel unfinished.
 *
 * On a phone the links leave the bar and become a bottom tab bar, where a
 * thumb already is. Both are rendered; CSS decides which one is visible, so
 * there is one set of links and no chance of the two drifting apart.
 *
 * A link is either a route (`to`) or a tab on this page (`onClick`), never
 * both. `short` is what the bottom bar uses when the full label is too long
 * for a thumb-width column — "Wishes I'm granting" becomes "Granting".
 */

export type NavLink = {
  label: string
  short?: string
  icon: React.ReactNode
  to?: string
  onClick?: () => void
  active?: boolean
}

export default function TopBar({
  links = [], alias, onSwitch, trailing,
}: {
  links?: NavLink[]
  alias?: string
  onSwitch?: () => void
  trailing?: React.ReactNode
}) {
  return (
    <>
      <header className="topbar">
        <div className="topbar__inner">
          <Link className="topbar__brand" to="/" aria-label="Wishing Tree, home">
            <Logo size={24} />
          </Link>

          <nav className="topbar__links" aria-label="Sections">
            {links.map((link) => <BarLink key={link.label} link={link} />)}
          </nav>

          <div className="topbar__right">
            {trailing}
            {alias && <AccountMenu alias={alias} onSwitch={onSwitch} />}
          </div>
        </div>
      </header>

      {links.length > 0 && (
        <nav className="tabbar" aria-label="Sections">
          {links.map((link) => (
            <BarLink key={link.label} link={link} bottom />
          ))}
        </nav>
      )}
    </>
  )
}

function BarLink({ link, bottom = false }: { link: NavLink; bottom?: boolean }) {
  const cls = bottom
    ? `tabbar__link${link.active ? ' tabbar__link--on' : ''}`
    : `topbar__link${link.active ? ' topbar__link--on' : ''}`
  const body = (
    <>
      {link.icon}
      <span>{bottom ? link.short ?? link.label : link.label}</span>
    </>
  )

  if (link.to) return <Link className={cls} to={link.to}>{body}</Link>
  return (
    <button type="button" className={cls} onClick={link.onClick}
            aria-current={link.active ? 'page' : undefined}>
      {body}
    </button>
  )
}

/**
 * The alias, with the part of it that actually distinguishes one person from
 * another. A first initial would read "N" for every neighbor in New Haven,
 * so the badge carries the code — A04, D01 — which is the whole point of an
 * alias.
 */
function AccountMenu({ alias, onSwitch }: { alias: string; onSwitch?: () => void }) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const code = alias.split(' ').pop() ?? alias

  useEffect(() => {
    if (!open) return
    function away(event: MouseEvent) {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    function escape(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', escape)
    }
  }, [open])

  return (
    <div className="account" ref={box}>
      <button
        type="button" className="account__btn"
        aria-expanded={open} aria-haspopup="menu"
        onClick={() => setOpen((was) => !was)}
      >
        <span className="account__badge" aria-hidden="true">{code}</span>
        <span className="account__alias">{alias}</span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>

      {open && (
        <div className="account__menu" role="menu">
          <p className="account__who">
            Signed in as<br /><strong>{alias}</strong>
          </p>
          <button type="button" className="account__item" role="menuitem" onClick={onSwitch}>
            Switch account
          </button>
        </div>
      )}
    </div>
  )
}
