import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronDown, HeartHandshake, HelpCircle, Info, ListChecks, LogIn,
  Repeat, Sparkles, TreePine, UserPlus,
} from 'lucide-react'
import Logo from './Logo'
import type { Me } from '../api'

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

/** What a visitor who is not signed in can get to from anywhere. */
const SIGNED_OUT: NavLink[] = [
  { label: 'How it works', short: 'How', to: '/how-it-works',
    icon: <HelpCircle size={17} aria-hidden="true" /> },
  { label: 'About', short: 'About', to: '/about',
    icon: <Info size={17} aria-hidden="true" /> },
  { label: 'Log in', short: 'Log in', to: '/login',
    icon: <LogIn size={17} aria-hidden="true" /> },
  { label: 'Create account', short: 'Sign up', to: '/family/signup',
    icon: <UserPlus size={17} aria-hidden="true" /> },
]

/**
 * A role's links as plain routes, for pages that are not that role's own
 * screen — About, say, reached from either side. The role's own page passes
 * its own set, where the first two switch tabs instead of navigating.
 */
export function roleLinks(role: 'family' | 'donor'): NavLink[] {
  const about: NavLink = {
    label: 'About', short: 'About', to: '/about',
    icon: <Info size={17} aria-hidden="true" />,
  }
  if (role === 'family') {
    return [
      { label: 'My wishes', short: 'Wishes', to: '/family',
        icon: <ListChecks size={17} aria-hidden="true" /> },
      { label: 'Make a wish', short: 'Ask', to: '/family',
        icon: <Sparkles size={17} aria-hidden="true" /> },
      about,
    ]
  }
  return [
    { label: 'Wish Tree', short: 'Tree', to: '/donor',
      icon: <TreePine size={17} aria-hidden="true" /> },
    { label: "Wishes I'm granting", short: 'Granting', to: '/donor',
      icon: <HeartHandshake size={17} aria-hidden="true" /> },
    about,
  ]
}

export default function TopBar({
  links, alias, me, onSwitch, onSwitchSide, trailing,
}: {
  links?: NavLink[]
  alias?: string
  me?: Me | null
  onSwitch?: () => void
  onSwitchSide?: (role: 'family' | 'donor') => void
  trailing?: React.ReactNode
}) {
  // No page is a dead end: with nobody signed in the bar still offers the
  // four ways on, rather than being a logo on its own.
  const shown = links ?? (alias ? [] : SIGNED_OUT)
  return (
    <>
      <header className="topbar">
        <div className="topbar__inner">
          <Link className="topbar__brand" to="/" aria-label="Wishing Tree, home">
            <Logo size={24} />
          </Link>

          <nav className="topbar__links" aria-label="Sections">
            {shown.map((link) => <BarLink key={link.label} link={link} />)}
          </nav>

          <div className="topbar__right">
            {trailing}
            {alias && (
              <AccountMenu
                alias={alias} me={me} onSwitch={onSwitch} onSwitchSide={onSwitchSide}
              />
            )}
          </div>
        </div>
      </header>

      {shown.length > 0 && (
        <nav className="tabbar" aria-label="Sections">
          {shown.map((link) => (
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
function AccountMenu({
  alias, me, onSwitch, onSwitchSide,
}: {
  alias: string
  me?: Me | null
  onSwitch?: () => void
  onSwitchSide?: (role: 'family' | 'donor') => void
}) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const code = alias.split(' ').pop() ?? alias
  const other = me?.roles?.find((r) => r.alias !== alias) ?? null

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
            {me?.email && <><br /><span className="account__email">{me.email}</span></>}
          </p>

          {/* One email may hold both sides. If this one does, moving between
              them is a menu item rather than a second login. */}
          {other && onSwitchSide && (
            <button
              type="button" className="account__item" role="menuitem"
              onClick={() => onSwitchSide(other.role)}
            >
              <Repeat size={14} aria-hidden="true" />
              Switch to {other.alias}
            </button>
          )}

          <button type="button" className="account__item" role="menuitem" onClick={onSwitch}>
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}
