/**
 * The three things a signed-in person can do to their own session.
 *
 * Kept out of `session.ts` so that module stays about *reading* who you are,
 * and out of the pages so that signing out means the same thing everywhere.
 */

import { chooseSide, logOut } from './api'
import { forgetMe, homePath, setMe } from './session'

/** Sign out, and land on the page you can always get to. */
export async function signOut(): Promise<void> {
  try {
    await logOut()
  } finally {
    // Even if the call failed, this browser is done with that session.
    forgetMe()
    window.location.assign('/')
  }
}

/** Move to the other side of an account that has both. */
export async function switchSide(role: 'family' | 'donor'): Promise<void> {
  const me = await chooseSide(role)
  setMe(me)
  window.location.assign(homePath(role))
}
