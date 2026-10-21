/** Thin wrappers over the JSON API. */

export type Category =
  | 'rent_utilities' | 'essentials' | 'clothing'
  | 'school_supplies' | 'household' | 'gifts' | 'food' | 'other'

export type Preference = 'specific' | 'flexible' | 'either'

export type Account = { role: 'family' | 'donor'; alias: string; zip: string; detail: string }

export const CATEGORY_LABELS: Record<Category, string> = {
  rent_utilities: 'Rent & utilities',
  essentials: 'Essentials (hygiene, diapers)',
  clothing: 'Clothing',
  school_supplies: 'School supplies',
  household: 'Household',
  gifts: 'Gifts',
  food: 'Food',
  other: 'Other',
}

/**
 * An error whose message was written for a person to read.
 *
 * Anything else — a dropped connection, a parse failure, a bug — is replaced
 * with a sentence we wrote. Nobody using this app should ever be shown
 * "Failed to fetch".
 */
export class UserMessage extends Error {}

export function userMessage(error: unknown, fallback: string): string {
  return error instanceof UserMessage && error.message ? error.message : fallback
}

const OFFLINE =
  'We could not reach Wishing Tree just then. Check your connection and try again.'

async function request<T>(path: string, init?: RequestInit, fallback?: string): Promise<T> {
  let response: Response
  try {
    // `same-origin` sends the session cookie, which every per-account
    // endpoint now requires. The app and the API share an origin, so this
    // never reaches anywhere else.
    response = await fetch(path, { credentials: 'same-origin', ...init })
  } catch {
    throw new UserMessage(OFFLINE)
  }

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = (data as { detail?: unknown }).detail
    throw new UserMessage(
      typeof detail === 'string'
        ? detail
        : fallback ?? 'Something went wrong. Please try again.',
    )
  }
  return data as T
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function signUpFamily(form: {
  zip: string
  contact_address: string
  contact_email: string
  contact_phone: string | null
  first_name: string | null
  password: string
}) {
  return post<{ role: 'family'; alias: string; zip: string }>('/api/families', form)
}

export function signUpDonor(form: {
  zip: string
  contact_address: string
  contact_email: string
  contact_phone: string | null
  first_name: string | null
  password: string
  budget_usd: number
  preferred_categories: Category[]
  preference: Preference
}) {
  return post<{ role: 'donor'; alias: string; zip: string }>('/api/donors', form)
}

export function unlockCoordinator(passcode: string) {
  return post<{ unlocked: boolean; token: string }>('/api/coordinator/unlock', { passcode })
}

export type AgentCall = {
  timestamp: string
  agent: string
  operation: string
  session_id: string | null
  request_id: number | null
  tools_called: string[]
  input_summary: string
  output_summary: string
  removed: string[]
  flags: { kind: string; reason: string }[]
  enforced: string[]
  input_tokens: number
  cached_input_tokens: number
  cache_write_tokens: number
  output_tokens: number
  latency_ms: number
  cost_usd: number | null
  ok: boolean
  error: string | null
  prompt_version: string | null
}

export type Activity = {
  calls: AgentCall[]
  totals: {
    calls: number
    input_tokens: number
    cached_input_tokens: number
    cache_write_tokens: number
    output_tokens: number
    cost_usd: number
    prices_are_placeholders: boolean
  }
  budget: {
    daily_tokens: number
    daily_cap: number
    daily_remaining: number
    session_cap: number
  }
  /** How long each finished intake took. Admin only. */
  intakes?: {
    session_id: string
    family_alias: string
    turns: number
    duration_seconds: number
    approved_at: string | null
  }[]
}

export function getActivity(token: string): Promise<Activity> {
  return request('/api/coordinator/activity',
    { headers: { 'X-Coordinator-Token': token } },
    'Coordinator access has expired. Enter the passcode again.')
}

export function listAccounts(): Promise<{ families: Account[]; donors: Account[] }> {
  return request('/api/accounts', undefined, 'We could not load the demo accounts.')
}

// --------------------------------------------------------------------- intake

export type Occasion =
  | 'holiday' | 'birthday' | 'back_to_school' | 'job_interview' | 'emergency' | 'everyday'

export const OCCASION_LABELS: Record<Occasion, string> = {
  holiday: 'Holiday',
  birthday: 'Birthday',
  back_to_school: 'Back to school',
  job_interview: 'Job interview',
  emergency: 'Emergency',
  everyday: 'Everyday',
}

export type DraftWish = {
  category: Category
  request_type: 'specific' | 'flexible'
  item_description: string
  occasion: Occasion
  deadline: string | null
  estimated_cost_usd: number | null
  budget_min_usd: number | null
  budget_max_usd: number | null
  product_link: string | null
  brand: string | null
  size: string | null
  color: string | null
  open_to_substitute: boolean
  size_preferences: string | null
}

export type Usage = {
  calls: number
  input_tokens: number
  cached_input_tokens: number
  cache_write_tokens: number
  output_tokens: number
  cost_usd: number
  latency_ms: number
  prices_are_placeholders: boolean
  model: string
}

export type IntakeStart = {
  session_id: string | null
  message: string
  at_wish_cap: boolean
  open_wishes: number
  maximum: number
  turns_remaining?: number
  usage?: Usage
}

export type IntakeTurn = {
  message: string
  draft_wishes: DraftWish[]
  done: boolean
  limit_reached: boolean
  turns_used: number
  turns_remaining: number
  blocked_lookups?: number[]
  usage: Usage
}

export type WishOutcome = {
  request_id: number
  published: boolean
  description: string
  removed: string[]
  flags: { kind: string; reason: string }[]
  enforced: string[]
  /** Why it was held, in our words. Null when it went up. The agent's own
   *  note never leaves the server — it lives in the activity log. */
  held_reason: string | null
  /** The wish as it now appears on the tree. Null for a held wish. */
  card: WishCard | null
}

export type IntakeApproval = {
  approved: number
  published: number
  held: number
  duration_seconds: number
  turns_used: number
  outcomes: WishOutcome[]
  usage: Usage
}

export function startIntake(familyAlias: string) {
  return post<IntakeStart>('/api/intake/start', { family_alias: familyAlias })
}

export function sendIntakeMessage(sessionId: string, message: string) {
  return post<IntakeTurn>('/api/intake/message', { session_id: sessionId, message })
}

export function approveIntake(sessionId: string, wishes: DraftWish[]) {
  return post<IntakeApproval>('/api/intake/approve', { session_id: sessionId, wishes })
}

// ---------------------------------------------------------------- donor side

export type WishCard = {
  id: number
  family_alias: string
  category: Category
  occasion: Occasion
  request_type: 'specific' | 'flexible'
  item_description: string
  zip: string
  deadline: string | null
  deadline_label: string
  days_until_deadline: number | null
  days_waiting: number
  estimated_cost_usd: number | null
  budget_min_usd: number | null
  budget_max_usd: number | null
  cost_ceiling_usd: number
  cost_is_estimate: boolean
  product_link: string | null
  brand: string | null
  size: string | null
  color: string | null
  open_to_substitute: boolean
  size_preferences: string | null
  status: string
  badges?: Badge[]
}

export type RegionInfo = {
  name: string
  hub_name: string
  hub_address: string
  dropoff_window: string
  delivery_window: string
}

export type WishWall = {
  count: number
  wishes: WishCard[]
  region: RegionInfo
  recently_granted: { id: number; category: Category }[]
  granted_window_days: number
}

export type Match = {
  request_id: number
  reason: string
  dropoff_date: string
  delivery_date: string
  arrives_in_time: boolean
  wish: WishCard
}

export type MatchResponse = {
  session_id: string
  matches: Match[]
  note: string
  enforced: string[]
  candidate_limit: number | null
  usage: Usage
}

export type Logistics =
  | { kind: 'direct_payment'; headline: string; detail: string; delivery_date: string }
  | {
      kind: 'hub_dropoff'; headline: string; hub_name: string; hub_address: string
      dropoff_date: string; dropoff_window: string
      delivery_date: string; delivery_window: string
    }

export type GrantResponse = {
  granted: boolean
  wish: WishCard
  paid_directly_to_provider: boolean
  logistics: Logistics
  arrives_in_time: boolean
  schedule_note: string
}

export type WallFilters = {
  categories: Category[]
  occasion: Occasion | ''
  requestType: 'specific' | 'flexible' | ''
  maxCost: string
}

export function getWishes(filters: WallFilters): Promise<WishWall> {
  const params = new URLSearchParams()
  filters.categories.forEach((c) => params.append('category', c))
  if (filters.occasion) params.set('occasion', filters.occasion)
  if (filters.requestType) params.set('request_type', filters.requestType)
  if (filters.maxCost) params.set('max_cost_usd', filters.maxCost)
  return request(`/api/wishes?${params}`, undefined, 'We could not load the tree.')
}

export function requestMatches(donorAlias: string, filters: WallFilters) {
  return post<MatchResponse>('/api/match', {
    donor_alias: donorAlias,
    max_cost_usd: filters.maxCost ? Number(filters.maxCost) : null,
    request_type: filters.requestType || null,
    categories: filters.categories.length ? filters.categories : null,
  })
}

export function grantWish(donorAlias: string, requestId: number, dropoffDate?: string) {
  return post<GrantResponse>('/api/grant', {
    donor_alias: donorAlias,
    request_id: requestId,
    dropoff_date: dropoffDate ?? null,
  })
}

// ------------------------------------------------------- deliveries & run sheet

export type WindowResponse = 'pending' | 'confirmed' | 'needs_reschedule'

export type Delivery = {
  pledge_id: number
  wish: WishCard
  delivery_date: string
  delivery_window: string
  status: 'scheduled' | 'delivered'
  window_response: WindowResponse
  paid_directly_to_provider: boolean
}

export function getDeliveries(familyAlias: string): Promise<{ deliveries: Delivery[] }> {
  return request(`/api/families/${encodeURIComponent(familyAlias)}/deliveries`,
    undefined, 'We could not load your deliveries just now.')
}

export function respondToWindow(
  familyAlias: string, pledgeId: number, response: 'confirmed' | 'needs_reschedule',
) {
  return post<{ message: string; coordinator_will_contact: boolean; window_response: WindowResponse }>(
    '/api/families/deliveries/respond',
    { family_alias: familyAlias, pledge_id: pledgeId, response },
  )
}

export type DropoffRow = {
  pledge_id: number
  donor_alias: string
  donor_address: string | null
  donor_phone: string | null
  item: string
  dropoff_date: string
  status: 'scheduled' | 'dropped off' | 'missed'
}

export type DeliveryRow = {
  family_alias: string
  family_address: string | null
  family_phone: string | null
  delivery_date: string
  pledge_ids: number[]
  items: string[]
  confirmed: boolean
  window_responses: WindowResponse[]
  status: 'scheduled' | 'delivered'
}

export type DirectPaymentRow = {
  pledge_id: number
  family_alias: string
  donor_alias: string
  item: string
  amount_usd: number
  pay_by: string
  status: string
  note: string
}

export type RunSheet = {
  week_start: string
  week_end: string
  is_this_week: boolean
  previous_week: string
  next_week: string
  hub: { name: string; address: string; dropoff_window: string; delivery_window: string }
  dropoffs: DropoffRow[]
  deliveries: DeliveryRow[]
  direct_payments: DirectPaymentRow[]
  counts: {
    dropoffs: number; deliveries: number; direct_payments: number
    awaiting_confirmation: number; needs_reschedule: number
  }
}

export function getRunSheet(token: string, weekOf?: string): Promise<RunSheet> {
  const query = weekOf ? `?week_of=${weekOf}` : ''
  return request(`/api/coordinator/run-sheet${query}`,
    { headers: { 'X-Coordinator-Token': token } },
    'Coordinator access has expired. Enter the passcode again.')
}

export function setPledgeStatus(
  token: string, pledgeIds: number[], status: string,
): Promise<{ reopened_wishes: number[]; note: string }> {
  return request('/api/coordinator/pledge-status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Coordinator-Token': token },
    body: JSON.stringify({ pledge_ids: pledgeIds, status }),
  }, 'We could not update that just now. Please try again.')
}

// ------------------------------------------------------ service area & stores

export type ServiceArea = {
  notice: string
  region: string
  zip_codes: string[]
  checked: boolean
  zip?: string
  covered?: boolean
  message?: string
}

export function getServiceArea(zip?: string): Promise<ServiceArea> {
  const query = zip ? `?zip=${encodeURIComponent(zip)}` : ''
  return request(`/api/service-area${query}`, undefined,
    'We could not check the service area just now.')
}

export function getRetailers(): Promise<{ count: number; stores: string[]; note: string }> {
  return request('/api/retailers', undefined, 'We could not load the store list.')
}

/** Format a US number as it is typed: (203) 555-0104. */
export function formatPhone(input: string): string {
  const digits = input.replace(/\D/g, '').slice(0, 11)
  const n = digits.startsWith('1') ? digits.slice(1) : digits
  if (n.length <= 3) return n
  if (n.length <= 6) return `(${n.slice(0, 3)}) ${n.slice(3)}`
  return `(${n.slice(0, 3)}) ${n.slice(3, 6)}-${n.slice(6, 10)}`
}

/** Is this link one of the stores we can post? Checked as text, never opened. */
export function linkIsAccepted(url: string, stores: string[]): boolean {
  if (!url.trim()) return true
  let host: string
  try {
    const parsed = new URL(url.trim())
    if (parsed.protocol !== 'https:') return false
    host = parsed.hostname.toLowerCase().replace(/^www\./, '')
  } catch {
    return false
  }
  return stores.some((s) => host === s || host.endsWith(`.${s}`))
}

// --------------------------------------------------------------- my wishes

export type WishProgress = {
  wish: WishCard
  stage: 'being_checked' | 'on_the_tree' | 'granted' | 'on_its_way' | 'delivered' | 'not_posted'
  label: string
  detail: string
  still_looking: boolean
  delivery: { pledge_id: number; date: string; window: string; window_response: WindowResponse } | null
  direct_payment: boolean
  direct_payment_note: string | null
  removed_before_posting: string[]
  /** The five stages with the current one marked. Null when a wish is held,
      because "Not on the tree yet" is off the track rather than early on it. */
  track: TrackStep[] | null
}

export type TrackStep = {
  key: string
  label: string
  done: boolean
  now: boolean
}

export function getMyWishes(alias: string): Promise<{
  count: number; wishes: WishProgress[]; open_wish_cap: number
}> {
  return request(`/api/families/${encodeURIComponent(alias)}/wishes`, undefined,
    'We could not load your wishes just now.')
}

// ------------------------------------------------------------- donor extras

export type Badge = { kind: 'needed_by' | 'waiting'; label: string; detail: string }

export type WhatToBring = {
  kind: 'specific' | 'flexible'
  headline: string
  item: string
  brand?: string | null
  size?: string | null
  color?: string | null
  link?: string | null
  essentials?: string | null
  substitute_ok: boolean
  substitute_note: string
}

export type DropoffChoice = {
  dropoff_date: string
  delivery_date: string
  arrives_in_time: boolean
  label: string
}

export type GrantOptions = {
  wish: WishCard
  donor_alias: string
  what_to_bring: WhatToBring | null
  estimated_cost_usd: number
  cost_is_estimate: boolean
  paid_directly_to_provider: boolean
  direct_payment_note: string | null
  dropoff_choices: DropoffChoice[]
  hub: { name: string; address: string; dropoff_window: string; delivery_window: string }
}

export function getGrantOptions(requestId: number, donorAlias: string) {
  return request<GrantOptions>(
    `/api/grant/options?request_id=${requestId}&donor_alias=${encodeURIComponent(donorAlias)}`,
    undefined, 'We could not open that wish just now.')
}

export type GrantedRow = {
  pledge_id: number
  wish: WishCard
  status: string
  label: string
  paid_directly_to_provider: boolean
  dropoff_date: string
  delivery_date: string
  dropoff_window: string
  hub_name: string
  hub_address: string
  hub_maps_url: string
  section: 'coming_up' | 'granted'
  can_release: boolean
}

export function getGranted(alias: string) {
  return request<{
    count: number; granted: GrantedRow[]; this_week: GrantedRow[]
    coming_up: GrantedRow[]; already_granted: GrantedRow[]
    hub: { name: string; address: string; maps_url: string; dropoff_window: string }
  }>(`/api/donors/${encodeURIComponent(alias)}/granted`, undefined,
    'We could not load what you have granted.')
}

export function releasePledge(pledgeId: number, donorAlias: string) {
  return request<{ released: boolean; message: string }>(
    `/api/pledges/${pledgeId}/release?donor_alias=${encodeURIComponent(donorAlias)}`,
    { method: 'POST' }, 'We could not release that just now.')
}

export function calendarUrl(pledgeId: number, donorAlias: string): string {
  return `/api/pledges/${pledgeId}/calendar.ics?donor_alias=${encodeURIComponent(donorAlias)}`
}


export type Stats = {
  wishes_granted: number
  wishes_open: number
  region: string
  line: string
}

/** Counted from the database every time. Nothing here is rounded up. */
export function getStats(): Promise<Stats> {
  return request('/api/stats', undefined, 'We could not load the numbers just now.')
}

// --------------------------------------------------------------------------
// Accounts
// --------------------------------------------------------------------------

export type RoleOption = { role: 'family' | 'donor'; alias: string; zip: string }

export type Me = {
  signed_in: boolean
  email?: string
  /** Their own first name, if they gave one. The only response in the app
   *  that carries it, and only ever to its owner. */
  first_name?: string | null
  role?: 'family' | 'donor' | null
  alias?: string | null
  zip?: string | null
  roles?: RoleOption[]
  must_choose?: boolean
}

export function getMe() {
  return request<Me>('/api/auth/me', undefined, 'We could not check your session.')
}

export function logIn(email: string, password: string) {
  return post<Me>('/api/auth/login', { email, password })
}

export function chooseSide(role: 'family' | 'donor') {
  return post<Me>('/api/auth/side', { role })
}

/** The demo shortcut. Works only while that seeded account still has the
 *  published demo password — see the server for why. */
export function demoLogIn(alias: string) {
  return post<Me>('/api/auth/demo', { alias })
}

export function logOut() {
  return post<{ signed_in: boolean }>('/api/auth/logout', {})
}

export function resetPassword(email: string, code: string, password: string) {
  return post<{ ok: boolean; message: string }>('/api/auth/reset', { email, code, password })
}

export function issueResetCode(token: string, alias: string) {
  return request<{ alias: string; code: string; expires_in_minutes: number; how: string }>(
    '/api/coordinator/reset-password',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Coordinator-Token': token },
      body: JSON.stringify({ alias }),
    },
    'We could not issue a reset code.',
  )
}

export type Health = {
  region: {
    name: string
    hub_name: string
    hub_address: string
    dropoff_window: string
    delivery_window: string
  }
}

export function getHealth() {
  return request<Health>('/api/health', undefined, 'We could not reach the server.')
}


// ------------------------------------------------------------------- the site

export type Site = {
  /** True only where the app is deployed as a public demo. */
  demo: boolean
  banner: string | null
}

export function getSite(): Promise<Site> {
  return request('/api/site', undefined, 'We could not read the site settings.')
}
