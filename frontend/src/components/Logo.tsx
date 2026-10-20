import { Link } from 'react-router-dom'

/**
 * The mark: a small tree whose canopy is three leaves, one of them gold.
 * Drawn here as inline SVG — no image files, nothing copied from anywhere.
 */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg
      className="logo__mark" width={size} height={size} viewBox="0 0 32 32"
      fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"
    >
      {/* trunk */}
      <path
        d="M16 30v-9.5" stroke="var(--evergreen-deep)" strokeWidth="2.2"
        strokeLinecap="round"
      />
      {/* a branch to the gold leaf */}
      <path
        d="M16 24.5c0-2 1.4-3.4 3.2-4" stroke="var(--evergreen-deep)"
        strokeWidth="1.6" strokeLinecap="round"
      />
      {/* left leaf */}
      <path
        d="M15 21c-4.8.6-8-1.6-8.6-5.6-.6-4 1.9-7.2 6.7-7.8 1.6 2.4 2.3 4.6 2.5 6.8.2 2.2-.1 4.4-.6 6.6z"
        fill="var(--evergreen)"
      />
      {/* right leaf */}
      <path
        d="M17 21c4.8.6 8-1.6 8.6-5.6.6-4-1.9-7.2-6.7-7.8-1.6 2.4-2.3 4.6-2.5 6.8-.2 2.2.1 4.4.6 6.6z"
        fill="var(--evergreen-soft)"
      />
      {/* crown leaf */}
      <path
        d="M16 16.5c-2.6-2.4-3.6-5.2-2.8-8.2.8-3 3-5.2 6.2-6.3 1.3 2.9 1.4 5.8.4 8.6-.9 2.4-2.2 4.4-3.8 5.9z"
        fill="var(--gold)"
      />
    </svg>
  )
}

/** The logo with its wordmark. Links home unless `plain` is set. */
export default function Logo({
  plain = false, size = 28,
}: { plain?: boolean; size?: number }) {
  const inner = (
    <>
      <LogoMark size={size} />
      <span className="logo__word">
        Wishing <span className="logo__word-accent">Tree</span>
      </span>
    </>
  )
  return plain
    ? <span className="logo">{inner}</span>
    : <Link to="/" className="logo logo--link">{inner}</Link>
}
