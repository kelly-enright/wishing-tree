import { useMemo, useState } from 'react'
import type { Category, WishCard as Wish } from '../api'
import CategoryIcon from './CategoryIcon'
import WishCard from './WishCard'

/**
 * The Wish Tree: every open wish is a leaf.
 *
 * The tree itself is one SVG; the leaves are real HTML buttons positioned on
 * top of it. That is deliberate — a button is focusable, has a proper hit
 * area, reads to a screen reader, and can hold a Lucide icon without any of
 * the contortions that putting interactive controls inside SVG requires.
 *
 * Leaves are 44px, which is the smallest comfortable tap target on a phone.
 * The canopy holds a fixed number of them; anything past that goes to the
 * list, with a line saying so. A tree that crams forty leaves into a space
 * meant for thirty is worse than a list, and the list always works.
 */

/**
 * Category colors, all drawn from the evergreen-to-terracotta range.
 *
 * None of them is amber, deliberately: gold means "already granted" on this
 * tree, and a food leaf that reads as gold would quietly tell a donor the
 * wish was taken when it is not.
 */
const LEAF_COLORS: Record<Category, string> = {
  rent_utilities: '#2F5D50',
  essentials: '#4A7A6B',
  clothing: '#6B8F5E',
  school_supplies: '#8A9A5B',
  gifts: '#C8664A',
  food: '#6E8B3D',
  other: '#55736C',
}

/** Deterministic positions in rings, so the tree looks the same every load. */
function canopyPositions(): { left: number; top: number; tilt: number }[] {
  const rings = [
    { count: 1, radius: 0, offset: 0 },
    { count: 6, radius: 13, offset: 0.4 },
    { count: 10, radius: 23, offset: 0.15 },
    { count: 13, radius: 32, offset: 0.55 },
  ]
  const out: { left: number; top: number; tilt: number }[] = []
  rings.forEach((ring) => {
    for (let i = 0; i < ring.count; i += 1) {
      const angle = ((i + ring.offset) / ring.count) * Math.PI * 2
      out.push({
        left: 50 + Math.cos(angle) * ring.radius * 1.12,
        // The canopy is wider than it is tall, and sits above the trunk.
        top: 36 + Math.sin(angle) * ring.radius * 0.78,
        tilt: Math.round(Math.cos(angle) * 18),
      })
    }
  })
  return out
}

type Leaf =
  | { kind: 'open'; wish: Wish; seat: number }
  | { kind: 'granted'; category: Category; seat: number }

export default function WishTree({
  wishes, granted, grantedWindowDays, onGrant, granting, onSeeList,
}: {
  wishes: Wish[]
  granted: { id: number; category: Category }[]
  grantedWindowDays: number
  onGrant: (wish: Wish) => void
  granting: number | null
  onSeeList: () => void
}) {
  const [openId, setOpenId] = useState<number | null>(null)
  const seats = useMemo(canopyPositions, [])

  const shown = wishes.slice(0, seats.length)
  const overflow = wishes.length - shown.length
  const goldSeats = Math.max(0, seats.length - shown.length)
  const gold = granted.slice(0, goldSeats)

  const leaves: Leaf[] = [
    ...shown.map((wish, i) => ({ kind: 'open' as const, wish, seat: i })),
    ...gold.map((g, i) => ({
      kind: 'granted' as const, category: g.category, seat: shown.length + i,
    })),
  ]

  const selected = shown.find((w) => w.id === openId) ?? null

  return (
    <div className="tree">
      <div className="tree__canvas">
        <svg className="tree__art" viewBox="0 0 400 420" aria-hidden="true">
          <ellipse cx="200" cy="398" rx="128" ry="16" fill="var(--evergreen-pale)" />
          {/* canopy backdrop */}
          <ellipse cx="200" cy="150" rx="176" ry="136" fill="#EAF1EC" />
          <ellipse cx="200" cy="146" rx="150" ry="114" fill="#E0EBE2" />
          {/* trunk and branches */}
          <path
            d="M186 392c0-54 2-96 6-128h16c4 32 6 74 6 128z"
            fill="#8A6442"
          />
          <path
            d="M196 268c-22-14-38-30-48-50M204 268c22-14 38-30 48-50M200 250c0-26 2-48 6-66M198 252c-14-16-24-34-28-54M202 252c14-16 24-34 28-54"
            stroke="#8A6442" strokeWidth="7" strokeLinecap="round" fill="none"
          />
        </svg>

        {leaves.map((leaf) => {
          const seat = seats[leaf.seat]
          const style = {
            left: `${seat.left}%`,
            top: `${seat.top}%`,
            transform: `translate(-50%, -50%) rotate(${seat.tilt}deg)`,
          }

          if (leaf.kind === 'granted') {
            return (
              <span
                key={`gold-${leaf.seat}`} style={style}
                className="leaf leaf--granted"
                title={`Already granted, in the last ${grantedWindowDays} days`}
                aria-label="A wish already granted"
              >
                <CategoryIcon category={leaf.category} size={18} />
              </span>
            )
          }

          const { wish } = leaf
          const urgent = (wish.badges ?? []).some((b) => b.kind === 'needed_by')
          return (
            <button
              key={wish.id} type="button" style={{ ...style, background: LEAF_COLORS[wish.category] }}
              className={`leaf leaf--open${openId === wish.id ? ' leaf--on' : ''}${urgent ? ' leaf--soon' : ''}`}
              onClick={() => setOpenId(openId === wish.id ? null : wish.id)}
              aria-pressed={openId === wish.id}
              aria-label={`${wish.item_description} — ${wish.family_alias}`}
            >
              <CategoryIcon category={wish.category} size={19} />
            </button>
          )
        })}
      </div>

      <p className="tree__legend">
        {wishes.length === 0
          ? 'No wishes match those filters right now.'
          : `${shown.length} wish${shown.length === 1 ? '' : 'es'} on the tree`}
        {gold.length > 0 && (
          <> · <span className="tree__gold">{gold.length} gold</span> granted in the
            last {grantedWindowDays} days</>
        )}
        {overflow > 0 && (
          <>
            {' '}·{' '}
            <button type="button" className="tree__more" onClick={onSeeList}>
              {overflow} more in the list
            </button>
          </>
        )}
      </p>

      {selected ? (
        <div className="tree__picked">
          <WishCard
            wish={selected}
            onGrant={onGrant}
            granting={granting === selected.id}
          />
          <button type="button" className="btn btn--light btn--small" onClick={() => setOpenId(null)}>
            Close
          </button>
        </div>
      ) : (
        wishes.length > 0 && (
          <p className="tree__hint">Tap a leaf to see the wish.</p>
        )
      )}
    </div>
  )
}
