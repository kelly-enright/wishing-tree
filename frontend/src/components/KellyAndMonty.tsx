import Monty from './Monty'

/**
 * Kelly and Monty, for the "Who I am" section of the About page.
 *
 * Drawn from scratch in the same flat style as Monty himself — no photograph,
 * no likeness of anyone. It is a friendly stand-in, the way a hand-drawn
 * avatar is, and it keeps the page self-contained: no image file to ship, and
 * it stays sharp at any size.
 *
 * Monty is the real `<Monty />` component rather than a copy of him, so the
 * two drawings cannot drift apart. He sits; the body under him is drawn here.
 *
 * The one Yale blue in the app lives on the crewneck. It is deliberately the
 * only place the page leaves the evergreen palette.
 */

const SKIN = '#F1D2B8'
const SKIN_SHADE = '#DFB997'
const HAIR = '#43291A'
const HAIR_LIFT = '#533526'
const YALE = '#00356B'
const HAZEL = '#8C7142'
const YALE_DEEP = '#002A52'

export default function KellyAndMonty({ size = 190 }: { size?: number }) {
  return (
    <svg
      className="portrait" width={size} height={size * 0.88}
      viewBox="0 0 200 176" fill="none" xmlns="http://www.w3.org/2000/svg"
      role="img" aria-label="An illustration of Kelly and her corgi, Monty"
    >
      <defs>
        {/* Both figures are clipped to the disc, so a sweatshirt hem or a
            paw runs off the edge instead of stopping flat inside it. */}
        <clipPath id="portrait-disc">
          <circle cx="100" cy="88" r="84" />
        </clipPath>
      </defs>

      {/* the soft disc they sit on */}
      <circle cx="100" cy="88" r="84" fill="var(--evergreen-pale)" />

      <g clipPath="url(#portrait-disc)">
      {/* ---------------------------------------------------------- Kelly */}
      {/* hair, behind everything */}
      <path
        d="M44 74c0-24 13-40 31-40s31 16 31 40c0 16-2 28-5 38H49c-3-10-5-22-5-38z"
        fill={HAIR}
      />

      {/* shoulders and crewneck */}
      <path
        d="M75 96c17 0 32 10 36 26l6 40H33l6-40c4-16 19-26 36-26z"
        fill={YALE}
      />
      {/* the ribbed neckline */}
      <path d="M62 99c4 7 9 11 13 11s9-4 13-11l-5-3c-3 4-5 6-8 6s-5-2-8-6z" fill={YALE_DEEP} />
      {/* sleeve seams, just enough to read as a sweatshirt */}
      <path d="M41 122c-3 9-5 21-6 40" stroke={YALE_DEEP} strokeWidth="2.5" strokeLinecap="round" />
      <path d="M109 122c3 9 5 21 6 40" stroke={YALE_DEEP} strokeWidth="2.5" strokeLinecap="round" />

      {/* the Y */}
      <path
        d="M66 124l9 11m9-11l-9 11m0 0v12"
        stroke="#FFFFFF" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round"
      />

      {/* neck */}
      <path d="M67 84h16v14c0 5-16 5-16 0z" fill={SKIN_SHADE} />

      {/* face */}
      <ellipse cx="75" cy="66" rx="23" ry="25" fill={SKIN} />

      {/* hair, in front: a center part falling either side */}
      <path d="M52 62c0-18 10-28 23-28s23 10 23 28c-4-9-10-14-23-14S56 53 52 62z" fill={HAIR_LIFT} />
      <path d="M52 60c-2 16-1 28 1 36-6-12-7-26-5-38z" fill={HAIR} />
      <path d="M98 60c2 16 1 28-1 36 6-12 7-26 5-38z" fill={HAIR} />

      {/* eyes — a hazel iris with a dark pupil, which still reads at 190px */}
      <circle cx="66" cy="66" r="3.4" fill={HAZEL} />
      <circle cx="84" cy="66" r="3.4" fill={HAZEL} />
      <circle cx="66" cy="66" r="1.7" fill="#2B2B2B" />
      <circle cx="84" cy="66" r="1.7" fill="#2B2B2B" />
      <circle cx="67.2" cy="64.8" r="1" fill="#FBF6EE" />
      <circle cx="85.2" cy="64.8" r="1" fill="#FBF6EE" />

      {/* brows, cheeks, a small smile */}
      <path d="M61 58c3-2 7-2 9 0" stroke={HAIR} strokeWidth="2.2" strokeLinecap="round" />
      <path d="M80 58c3-2 7-2 9 0" stroke={HAIR} strokeWidth="2.2" strokeLinecap="round" />
      <ellipse cx="60" cy="74" rx="4" ry="3" fill="#E08E8E" opacity="0.5" />
      <ellipse cx="90" cy="74" rx="4" ry="3" fill="#E08E8E" opacity="0.5" />
      <path d="M69 77c3 3 9 3 12 0" stroke="#2B2B2B" strokeWidth="2.2" strokeLinecap="round" />

      {/* ---------------------------------------------------------- Monty */}
      <g transform="translate(116 86)">
        {/* the sitting body, drawn under his head in his own coat colors */}
        <path d="M14 46c0-16 7-28 17-28s17 12 17 28c0 8-1 14-2 18H16c-1-4-2-10-2-18z" fill="#D5713F" />
        <path d="M23 50c0-10 4-17 8-17s8 7 8 17c0 6-1 11-2 14H25c-1-3-2-8-2-14z" fill="#FBF6EE" />
        {/* front paws */}
        <ellipse cx="24" cy="63" rx="6" ry="4" fill="#FBF6EE" />
        <ellipse cx="38" cy="63" rx="6" ry="4" fill="#FBF6EE" />
        <Monty size={62} mood="happy" />
      </g>
      </g>
    </svg>
  )
}
