import { useEffect, useRef, useState } from 'react'
import { HeartHandshake, PackageCheck, Sparkles } from 'lucide-react'
import CategoryIcon from './CategoryIcon'
import { CATEGORY_LABELS, type Category } from '../api'

/**
 * The pieces that make the landing page a picture of the thing rather than a
 * description of it. Everything here is drawn from components the app
 * already uses — the same icons on the same cards — so what a visitor sees
 * is what they get.
 */

// --------------------------------------------------------------------- count

/**
 * A number that counts up once, on arrival.
 *
 * Short and eased, so it reads as the page settling rather than a slot
 * machine. Someone who has asked for less motion simply gets the number.
 */
export function CountUp({ to, duration = 900 }: { to: number; duration?: number }) {
  const [shown, setShown] = useState(to)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    setShown(0)
    const begun = performance.now()
    let frame = 0
    const step = (now: number) => {
      const through = Math.min(1, (now - begun) / duration)
      // Ease out: quick at first, then settling, which is how a number
      // landing somewhere should feel.
      setShown(Math.round(to * (1 - Math.pow(1 - through, 3))))
      if (through < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [to, duration])

  return <>{shown}</>
}

// ------------------------------------------------------------------- reveal

/**
 * Fades its children in when they are scrolled to, once.
 *
 * `delay` staggers a row of them. Anyone with reduced motion set sees them
 * immediately, in place, because the alternative is content that never
 * appears if the observer misbehaves.
 */
export function Reveal({
  children, delay = 0,
}: { children: React.ReactNode; delay?: number }) {
  const box = useRef<HTMLDivElement>(null)
  const [shown, setShown] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )

  useEffect(() => {
    if (shown || !box.current) return
    const watcher = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setShown(true) },
      { rootMargin: '0px 0px -10% 0px' },
    )
    watcher.observe(box.current)
    return () => watcher.disconnect()
  }, [shown])

  return (
    <div
      ref={box}
      className={`reveal${shown ? ' reveal--in' : ''}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  )
}

// -------------------------------------------------------------- how it works

const STEPS = [
  {
    icon: <Sparkles size={26} aria-hidden="true" />,
    title: 'Make a wish',
    body: 'Tell us what would help, in your own words. We turn it into a wish and check it for anything identifying.',
  },
  {
    icon: <HeartHandshake size={26} aria-hidden="true" />,
    title: 'A neighbor grants it',
    body: 'Someone nearby sees it on the tree, picks it, and buys it. They never learn who asked.',
  },
  {
    icon: <PackageCheck size={26} aria-hidden="true" />,
    title: 'We deliver it',
    body: 'They drop it at Yale School of Management on Thursday, and we bring it to your door on Saturday.',
  },
]

export function ThreeSteps() {
  return (
    <ol className="steps">
      {STEPS.map((step, i) => (
        <li key={step.title}>
          <Reveal delay={i * 140}>
            <div className="steps__card">
              <span className="steps__icon">{step.icon}</span>
              <span className="steps__n">{i + 1}</span>
              <h3 className="steps__title">{step.title}</h3>
              <p className="steps__body">{step.body}</p>
            </div>
          </Reveal>
        </li>
      ))}
    </ol>
  )
}

// ---------------------------------------------------------- the range of it

/** Six categories, each with the icon it carries everywhere else in the app. */
const RANGE: { category: Category; label: string }[] = [
  { category: 'clothing', label: 'Coats' },
  { category: 'school_supplies', label: 'School supplies' },
  { category: 'essentials', label: 'Diapers' },
  { category: 'gifts', label: 'Birthday gifts' },
  { category: 'household', label: 'Household items' },
  { category: 'rent_utilities', label: 'Help with a bill' },
]

export function CategoryRange() {
  return (
    <ul className="range" aria-label="The kinds of wishes on the tree">
      {RANGE.map(({ category, label }) => (
        <li key={category} className="range__item">
          <span className="range__icon" title={CATEGORY_LABELS[category]}>
            <CategoryIcon category={category} size={22} />
          </span>
          {label}
        </li>
      ))}
    </ul>
  )
}

// -------------------------------------------------------------------- hills

/**
 * Two soft rises of sage behind the base of the tree.
 *
 * Without them the tree floats on cream. They are drawn wider than the tree
 * and bled off both edges, so they read as ground going on rather than as a
 * shape that happens to sit under it.
 */
export function Hills() {
  return (
    <svg
      className="hills" viewBox="0 0 600 120" preserveAspectRatio="none"
      aria-hidden="true" focusable="false"
    >
      <path
        d="M0 86c74-26 136-30 208-12 70 17 118 22 180 8 54-12 118-16 212 2v36H0z"
        fill="var(--hill-sage)"
      />
      <path
        d="M0 104c96-20 160-20 236-6 78 15 136 16 204 4 50-9 110-12 160-2v20H0z"
        fill="var(--hill-sage-deep)" opacity="0.75"
      />
    </svg>
  )
}

// --------------------------------------------------------------- background

/**
 * A few leaves drifting, far behind everything.
 *
 * Deliberately almost invisible: 6% opacity, half a minute to cross the page.
 * `aria-hidden`, no pointer events, and gone entirely under reduced motion.
 */
export function DriftingLeaves() {
  return (
    <div className="drift layer" aria-hidden="true">
      {LEAVES.map((leaf, i) => (
        <span key={i} className="drift__fall" style={leaf.fall}>
          <span className="drift__leaf" style={leaf.spin} />
        </span>
      ))}
    </div>
  )
}

/**
 * Nine leaves, each with its own lane, speed, sway and spin.
 *
 * Written out rather than randomised so the page looks the same every load —
 * and so each one can be placed deliberately. The lanes favour the margins:
 * the content column is centered and capped at 1120px, so on anything wide
 * these fall beside the text rather than behind it. They sit under
 * everything regardless, and take no clicks.
 */
const LEAVES: { fall: React.CSSProperties; spin: React.CSSProperties }[] = [
  { fall: { left: '4%',  animationDuration: '19s', animationDelay: '-3s' },
    spin: { animationDuration: '7s',  background: 'var(--evergreen-soft)' } },
  { fall: { left: '11%', animationDuration: '24s', animationDelay: '-14s' },
    spin: { animationDuration: '9s',  background: 'var(--evergreen)' } },
  { fall: { left: '19%', animationDuration: '16s', animationDelay: '-8s' },
    spin: { animationDuration: '6s',  background: 'var(--gold)' } },
  { fall: { left: '31%', animationDuration: '22s', animationDelay: '-19s' },
    spin: { animationDuration: '8s',  background: 'var(--evergreen-soft)' } },
  { fall: { left: '48%', animationDuration: '25s', animationDelay: '-11s' },
    spin: { animationDuration: '10s', background: 'var(--evergreen-pale)' } },
  { fall: { left: '64%', animationDuration: '18s', animationDelay: '-22s' },
    spin: { animationDuration: '7.5s', background: 'var(--evergreen)' } },
  { fall: { left: '77%', animationDuration: '21s', animationDelay: '-5s' },
    spin: { animationDuration: '8.5s', background: 'var(--gold-deep)' } },
  { fall: { left: '88%', animationDuration: '17s', animationDelay: '-16s' },
    spin: { animationDuration: '6.5s', background: 'var(--evergreen-soft)' } },
  { fall: { left: '95%', animationDuration: '23s', animationDelay: '-9s' },
    spin: { animationDuration: '9.5s', background: 'var(--evergreen)' } },
]
