/**
 * Who this browser is signed in as.
 *
 * The answer lives on the server now. Before accounts it was a line in
 * localStorage, which meant anyone could type an alias into it and be that
 * person; the API trusted whatever arrived. Now a session is a signed cookie
 * the browser cannot read, every per-account endpoint checks it, and this
 * module just caches what `/api/auth/me` says so that every component does
 * not ask again.
 *
 * The coordinator passcode is still separate, and still in sessionStorage:
 * it unlocks screens showing home addresses, so it should die with the tab.
 */

import { useEffect, useState } from 'react'
import { getMe, type Me, type RoleOption } from './api'

export type Role = 'family' | 'donor'
export type Session = { email: string; role: Role; alias: string; zip: string }

const COORDINATOR_KEY = 'wishingtree.coordinator'
const LEGACY_KEY = 'wishingtree.session'

let cached: Me | null = null
const listeners = new Set<() => void>()

/** Ask the server, once, and remember the answer. */
export async function loadMe(force = false): Promise<Me> {
  if (cached && !force) return cached
  try {
    cached = await getMe()
  } catch {
    cached = { signed_in: false }
  }
  // An old browser-only session from before accounts is meaningless now and
  // would only confuse anyone who still has one.
  try { localStorage.removeItem(LEGACY_KEY) } catch { /* storage off */ }
  return cached
}

export function cachedMe(): Me | null {
  return cached
}

export function setMe(me: Me): void {
  cached = me
  listeners.forEach((fn) => fn())
}

export function forgetMe(): void {
  cached = { signed_in: false }
  listeners.forEach((fn) => fn())
}

export function onSessionChange(fn: () => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

/** The current session as the pages want it, or null. */
export function sessionFrom(me: Me | null): Session | null {
  if (!me?.signed_in || !me.role || !me.alias) return null
  return { email: me.email ?? '', role: me.role, alias: me.alias, zip: me.zip ?? '' }
}

export function otherSide(me: Me | null): RoleOption | null {
  if (!me?.signed_in || !me.roles) return null
  return me.roles.find((r) => r.role !== me.role) ?? null
}

/** Where a role's own screen lives. */
export function homePath(role: Role): string {
  return role === 'family' ? '/family' : '/donor'
}

/**
 * The session, for components.
 *
 * `loading` matters: before the server answers we do not know whether anyone
 * is signed in, and guessing produces a flash of the wrong page — the login
 * screen for somebody who is already in, or the other way round.
 */
export function useSession(): { me: Me | null; session: Session | null; loading: boolean } {
  const [me, setLocal] = useState<Me | null>(cachedMe())
  const [loading, setLoading] = useState(cachedMe() === null)

  useEffect(() => {
    let alive = true
    if (cachedMe() === null) {
      loadMe().then((fresh) => {
        if (!alive) return
        setLocal(fresh)
        setLoading(false)
      })
    } else {
      setLoading(false)
    }
    return onSessionChange(() => {
      if (alive) setLocal(cachedMe())
    })
  }, [])

  return { me, session: sessionFrom(me), loading }
}

// ---------------------------------------------------------------- admin

/** The old name, kept because several screens read it. */
export function coordinatorToken(): string | null {
  return getCoordinatorToken()
}

export function isCoordinatorUnlocked(): boolean {
  return getCoordinatorToken() !== null
}

export function getCoordinatorToken(): string | null {
  try {
    return sessionStorage.getItem(COORDINATOR_KEY)
  } catch {
    return null
  }
}

export function setCoordinatorToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(COORDINATOR_KEY, token)
    else sessionStorage.removeItem(COORDINATOR_KEY)
  } catch { /* storage off */ }
}
