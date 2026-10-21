/**
 * Dates, as a person reads them.
 *
 * The API sends dates as plain ISO days — "2026-10-22" — which is the right
 * thing for data and the wrong thing to put on a screen. Everything a
 * neighbor or a wish granter sees goes through here first. The admin run
 * sheet is the exception: it is a working document, scanned in columns, and
 * keeps the compact ISO form.
 *
 * One trap worth naming. `new Date('2026-10-22')` is parsed as UTC midnight,
 * so anywhere west of Greenwich it renders as the 21st. Every date here is
 * built field by field in local time instead, which is also why none of this
 * uses the Date constructor's string form.
 */

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]
const DAYS_LONG = [
  'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
]
const DAYS_SHORT = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/** An ISO day as a local Date, or null if it is not one. */
export function parseDay(iso: string | null | undefined): Date | null {
  if (!iso) return null
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  if (!m) return null
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
  return Number.isNaN(d.getTime()) ? null : d
}

/** "Thursday, Oct 22" */
export function longDay(iso: string | null | undefined): string {
  const d = parseDay(iso)
  if (!d) return ''
  return `${DAYS_LONG[d.getDay()]}, ${MONTHS[d.getMonth()]} ${d.getDate()}`
}

/** "Thu, Oct 22" — for tighter spots like a card's metadata line. */
export function shortDay(iso: string | null | undefined): string {
  const d = parseDay(iso)
  if (!d) return ''
  return `${DAYS_SHORT[d.getDay()]}, ${MONTHS[d.getMonth()]} ${d.getDate()}`
}

/**
 * "4:00 PM-7:00 PM" → "4–7 PM".
 *
 * The window arrives from the server as `Window.label()`, which leads with the
 * weekday: "Thursday 4:00 PM-7:00 PM". We drop that weekday, because the date
 * beside it already says which day, and two of them reads like a stutter.
 * Anything that does not match the expected shape is passed through unharmed.
 */
export function hours(windowLabel: string | null | undefined): string {
  if (!windowLabel) return ''
  // Strip the leading weekday only — a label we do not recognize is left
  // whole, so "by arrangement" does not come back as "arrangement".
  const times = windowLabel.replace(
    /^(?:Sun|Mon|Tues?|Wed(?:nes)?|Thur?s?|Fri|Sat(?:ur)?)(?:day)?\s+/i, '')
  const m = /^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$/i
    .exec(times.trim())
  if (!m) return times
  const [, h1, m1, s1, h2, m2, s2] = m
  const from = m1 && m1 !== '00' ? `${h1}:${m1}` : h1
  const to = m2 && m2 !== '00' ? `${h2}:${m2}` : h2
  // "4 PM–7 PM" says PM twice for no reason; "4–7 PM" does not.
  return s1.toUpperCase() === s2.toUpperCase()
    ? `${from}–${to} ${s2.toUpperCase()}`
    : `${from} ${s1.toUpperCase()}–${to} ${s2.toUpperCase()}`
}

/** "Thursday, Oct 22, 4–7 PM" */
export function when(iso: string | null | undefined, windowLabel?: string | null): string {
  const day = longDay(iso)
  const time = hours(windowLabel)
  if (!day) return time
  return time ? `${day}, ${time}` : day
}

/** How far off a date is, in words: "today", "tomorrow", "in 5 days". */
export function awayFrom(iso: string | null | undefined, today = new Date()): string {
  const d = parseDay(iso)
  if (!d) return ''
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const days = Math.round((d.getTime() - start.getTime()) / 86_400_000)
  if (days === 0) return 'today'
  if (days === 1) return 'tomorrow'
  if (days === -1) return 'yesterday'
  if (days < 0) return `${-days} days ago`
  return `${days} days`
}

/**
 * "Sat, Oct 25 · 5 days" — a deadline with how long is left.
 * Past deadlines read "Sat, Oct 25 · 2 days ago" rather than "-2 days".
 */
export function deadline(iso: string | null | undefined, today = new Date()): string {
  const day = shortDay(iso)
  if (!day) return ''
  return `${day} · ${awayFrom(iso, today)}`
}
