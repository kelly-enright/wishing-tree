/**
 * Who this browser is signed in as.
 *
 * There are no passwords in the MVP. Signing up creates the record on the
 * server and returns an alias; that alias is all we keep here, so nothing
 * sensitive is stored in the browser.
 *
 * The coordinator is different: that passcode unlocks screens showing home
 * addresses, so it lives in sessionStorage and is gone when the tab closes.
 */

export type Role = 'family' | 'donor'

export type Session = {
  role: Role
  alias: string
  zip: string
}

const SESSION_KEY = 'wishingtree.session'
const COORDINATOR_KEY = 'wishingtree.coordinator'

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Session
    return parsed?.alias && parsed?.role ? parsed : null
  } catch {
    return null
  }
}

export function setSession(session: Session): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY)
}

export function isCoordinatorUnlocked(): boolean {
  return sessionStorage.getItem(COORDINATOR_KEY) === 'unlocked'
}

export function setCoordinatorUnlocked(unlocked: boolean): void {
  if (unlocked) sessionStorage.setItem(COORDINATOR_KEY, 'unlocked')
  else sessionStorage.removeItem(COORDINATOR_KEY)
}

export function homePath(role: Role): string {
  return role === 'family' ? '/family' : '/donor'
}
