/**
 * Monty — a Pembroke Welsh corgi, drawn here from scratch in SVG.
 *
 * Red-and-white: a warm red-fox coat with a white blaze, muzzle, chest and
 * paws, big upright ears, and no tail, which is the Pembroke of it.
 *
 * Nothing here is traced or copied. He is a handful of ellipses and paths,
 * and he inherits the app's palette so he sits in the page rather than on it.
 *
 * `mood` changes nothing about the drawing except the eyes and the tongue:
 *  - "happy"  — the donor side, where a bit of warmth is welcome
 *  - "calm"   — the family side, where someone may be having a hard week and
 *               a grinning dog is the wrong note
 */
export default function Monty({
  size = 72, mood = 'happy',
}: { size?: number; mood?: 'happy' | 'calm' }) {
  const happy = mood === 'happy'
  return (
    <svg
      className="monty" width={size} height={size} viewBox="0 0 96 96"
      fill="none" xmlns="http://www.w3.org/2000/svg" role="img"
      aria-label="Monty, a corgi"
    >
      {/* ears */}
      <path d="M22 36C19 25 21 14 26 12c5-2 11 7 13 18z" fill="#C8663B" />
      <path d="M74 36c3-11 1-22-4-24-5-2-11 7-13 18z" fill="#C8663B" />
      <path d="M25 33c-2-8-1-15 2-16s7 5 8 12z" fill="#F0C3A8" />
      <path d="M71 33c2-8 1-15-2-16s-7 5-8 12z" fill="#F0C3A8" />

      {/* head */}
      <ellipse cx="48" cy="52" rx="28" ry="24" fill="#D5713F" />

      {/* white blaze and muzzle */}
      <path d="M48 28c4 0 7 4 8 10s-1 12-8 12-10-6-8-12 4-10 8-10z" fill="#FBF6EE" />
      <ellipse cx="48" cy="63" rx="16" ry="12" fill="#FBF6EE" />

      {/* cheeks */}
      <ellipse cx="29" cy="58" rx="7" ry="6" fill="#FBF6EE" opacity="0.85" />
      <ellipse cx="67" cy="58" rx="7" ry="6" fill="#FBF6EE" opacity="0.85" />

      {/* eyes */}
      {happy ? (
        <>
          <path d="M34 48c2-3 6-3 8 0" stroke="#2B2B2B" strokeWidth="3" strokeLinecap="round" />
          <path d="M54 48c2-3 6-3 8 0" stroke="#2B2B2B" strokeWidth="3" strokeLinecap="round" />
        </>
      ) : (
        <>
          <circle cx="38" cy="49" r="3.2" fill="#2B2B2B" />
          <circle cx="58" cy="49" r="3.2" fill="#2B2B2B" />
          <circle cx="39.2" cy="48" r="1.1" fill="#FBF6EE" />
          <circle cx="59.2" cy="48" r="1.1" fill="#FBF6EE" />
        </>
      )}

      {/* nose and mouth */}
      <ellipse cx="48" cy="59" rx="4.6" ry="3.4" fill="#2B2B2B" />
      <path d="M48 62.5v3" stroke="#2B2B2B" strokeWidth="2" strokeLinecap="round" />
      <path
        d={happy ? "M41 66c3 4 11 4 14 0" : "M42 66.5c3 2.5 9 2.5 12 0"}
        stroke="#2B2B2B" strokeWidth="2.4" strokeLinecap="round"
      />
      {happy && <path d="M44 69c2 4 6 4 8 0z" fill="#E08E8E" />}
    </svg>
  )
}

/** Monty with a line beside him. Used in empty states and headers. */
export function MontySays({
  children, mood = 'happy', size = 56,
}: { children: React.ReactNode; mood?: 'happy' | 'calm'; size?: number }) {
  return (
    <div className={`montysays montysays--${mood}`}>
      <Monty size={size} mood={mood} />
      <p className="montysays__text">{children}</p>
    </div>
  )
}
