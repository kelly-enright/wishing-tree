/** Thin wrappers over the JSON API. */

export type Category =
  | 'rent_utilities' | 'essentials' | 'clothing'
  | 'school_supplies' | 'gifts' | 'food' | 'other'

export type Preference = 'specific' | 'flexible' | 'either'

export type Account = { role: 'family' | 'donor'; alias: string; zip: string; detail: string }

export const CATEGORY_LABELS: Record<Category, string> = {
  rent_utilities: 'Rent & utilities',
  essentials: 'Essentials (hygiene, diapers)',
  clothing: 'Clothing',
  school_supplies: 'School supplies',
  gifts: 'Gifts',
  food: 'Food',
  other: 'Other',
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = (data as { detail?: unknown }).detail
    throw new Error(
      typeof detail === 'string' ? detail : 'Something went wrong. Please try again.',
    )
  }
  return data as T
}

export function signUpFamily(form: { zip: string; contact_address: string; contact_phone: string }) {
  return post<{ role: 'family'; alias: string; zip: string }>('/api/families', form)
}

export function signUpDonor(form: {
  zip: string
  contact_address: string
  contact_phone: string
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
}

export async function getActivity(token: string): Promise<Activity> {
  const response = await fetch('/api/coordinator/activity', {
    headers: { 'X-Coordinator-Token': token },
  })
  if (!response.ok) throw new Error('Coordinator access has expired.')
  return response.json()
}

export async function listAccounts(): Promise<{ families: Account[]; donors: Account[] }> {
  const response = await fetch('/api/accounts')
  if (!response.ok) throw new Error('Could not load the demo accounts.')
  return response.json()
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
  note_to_family: string
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
