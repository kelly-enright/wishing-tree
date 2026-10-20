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
  return post<{ unlocked: boolean }>('/api/coordinator/unlock', { passcode })
}

export async function listAccounts(): Promise<{ families: Account[]; donors: Account[] }> {
  const response = await fetch('/api/accounts')
  if (!response.ok) throw new Error('Could not load the demo accounts.')
  return response.json()
}
