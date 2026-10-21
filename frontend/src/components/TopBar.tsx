import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  ChevronDown, HeartHandshake, HelpCircle, Info, ListChecks, LogIn, Menu,
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
  /** A small number beside the label — how many things are waiting. */
  count?: number
}

/** What a signed-out visitor can read about. Where they *act* sits on the
 *  right, the way almost every site puts it. */
const SIGNED_OUT: NavLink[] = [
  { label: 'How it works', short: 'How', to: '/how-it-works',
    icon: <HelpCircle size={17} aria-hidden="true" /> },
  { label: 'About', short: 'About', to: '/about',
    icon: <Info size={17} aria-hidden="true" /> },
]

/**
 * A role's links as plain routes, for pages that are not that role's own
 * screen — About, say, reached from either side. The role's own page passes
 * its own set, where the first two switch tabs instead of navigating.
 */
/**
 * The neighbor's links. Two pages, not two halves of one, so the highlight is
 * decided by which page you are on rather than by where you have scrolled.
 */
export function neighborLinks(on?: 'wishes' | 'new'): NavLink[] {
  return [
    { label: 'My wishes', short: 'Wishes', to: '/family',
      icon: <ListChecks size={17} aria-hidden="true" />,
      active: on ? on === 'wishes' : undefined },
    { label: 'Make a wish', short: 'Ask', to: '/family/new',
      icon: <Sparkles size={17} aria-hidden="true" />,
      active: on ? on === 'new' : undefined },
    { label: 'About', short: 'About', to: '/about',
      icon: <Info size={17} aria-hidden="true" /> },
  ]
}

export function roleLinks(role: 'family' | 'donor'): NavLink[] {
  const about: NavLink = {
    label: 'About', short: 'About', to: '/about',
    icon: <Info size={17} aria-hidden="true" />,
  }
  if (role === 'family') {
    // No `on` argument: nothing is the current page, so the bar falls back
    // to matching the route. On About that lights About, which is where you
    // are — reusing neighborLinks('wishes') here lit "My wishes" instead.
    return [...neighborLinks().slice(0, 2), about]
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
  // Which page we are on, so its own link is lit rather than looking like
  // somewhere else to go.
  const here = useLocation().pathname
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

          {/* Signed out on a phone there is no bottom tab bar to hold them,
              so How it works and About would be unreachable. This button is
              the only place they live at that width. */}
          {!alias && !links && <SignedOutMenu links={shown} />}

          <div className="topbar__right">
            {trailing}

            {/* Signed out: the two ways in, on the right. "Create account" is
                the filled one, because it is what a first-time visitor is
                most likely to want. */}
            {!alias && !links && (
              <>
                <Link
                  className={`topbar__link${here === '/login' ? ' topbar__link--on' : ''}`}
                  to="/login"
                >
                  <LogIn size={17} aria-hidden="true" />
                  <span className="full">Log in</span>
                </Link>
                <Link className="btn btn--primary btn--small" to="/family/signup">
                  <UserPlus size={15} aria-hidden="true" />
                  <span className="full">Create account</span>
                  <span className="short">Sign up</span>
                </Link>
              </>
            )}

            {alias && (
              <AccountMenu
                alias={alias} me={me} onSwitch={onSwitch} onSwitchSide={onSwitchSide}
              />
            )}
          </div>
        </div>
      </header>

      {/* Only for a signed-in person's own sections. A signed-out visitor
          reaches How it works and About from the menu button above, and
          having both did not fit on a 390px phone. */}
      {shown.length > 0 && (alias || links) && (
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
  const here = useLocation().pathname
  const active = link.active ?? (link.to ? here === link.to : false)
  const cls = bottom
    ? `tabbar__link${active ? ' tabbar__link--on' : ''}`
    : `topbar__link${active ? ' topbar__link--on' : ''}`
  const body = (
    <>
      {link.icon}
      <span>{bottom ? link.short ?? link.label : link.label}</span>
      {link.count ? <span className="navcount">{link.count}</span> : null}
    </>
  )

  if (link.to) return <Link className={cls} to={link.to}>{body}</Link>
  return (
    <button type="button" className={cls} onClick={link.onClick}
            aria-current={active ? 'page' : undefined}>
      {body}
    </button>
  )
}

function SignedOutMenu({ links }: { links: NavLink[] }) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const away = (e: MouseEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false)
    }
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', away)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('keydown', escape)
    }
  }, [open])

  return (
    <div className="phonemenu" ref={box}>
      <button
        type="button" className="phonemenu__btn"
        aria-expanded={open} aria-haspopup="menu" aria-label="Menu"
        onClick={() => setOpen((was) => !was)}
      >
        <Menu size={19} aria-hidden="true" />
      </button>

      {open && (
        <div className="account__menu" role="menu">
          {links.map((link) => (
            <Link
              key={link.label} to={link.to ?? '/'} role="menuitem"
              className="account__item" onClick={() => setOpen(false)}
            >
              {link.icon}
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Who you are, to you.
 *
 * Your name if you gave one — it is yours, and only you and the coordinator
 * ever see it. The alias is what everyone else sees, so the menu says so
 * rather than leaving you to guess which of the two strangers read.
 *
 * With no name, the alias does both jobs and the badge carries its code:
 * a first initial taken from "Neighbor A04" would read "N" for every
 * neighbor in New Haven.
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
  const name = me?.first_name?.trim() || null
  const code = name
    ? name.charAt(0).toUpperCase()
    : alias.split(' ').pop() ?? alias
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
        <span className="account__alias">{name ?? alias}</span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>

      {open && (
        <div className="account__menu" role="menu">
          <p className="account__who">
            Signed in as<br /><strong>{name ?? alias}</strong>
            {name && (
              <><br /><span className="account__alias-note">
                Others see you as {alias}.
              </span></>
            )}
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
