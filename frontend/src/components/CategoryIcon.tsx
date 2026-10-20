import {
  Apple, Gift, House, Pencil, Shirt, SprayCan, Star,
} from 'lucide-react'
import type { Category } from '../api'

/**
 * One icon per category, from Lucide (ISC licensed, bundled with the app).
 *
 * The icons are a second way to read a card at a glance — colour and shape
 * before words — which matters on a wall of thirty wishes on a phone.
 */
const ICONS = {
  rent_utilities: House,
  essentials: SprayCan,
  clothing: Shirt,
  school_supplies: Pencil,
  gifts: Gift,
  food: Apple,
  other: Star,
} as const

export default function CategoryIcon({
  category, size = 18,
}: { category: Category; size?: number }) {
  const Icon = ICONS[category] ?? Star
  return <Icon size={size} strokeWidth={2} aria-hidden="true" className="caticon" />
}
