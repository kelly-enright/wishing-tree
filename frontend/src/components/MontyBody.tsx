/**
 * Monty from the side, whole.
 *
 * The same flat vocabulary as his face: solid shapes, no gradients, no
 * outlines, the app's own palette. A Pembroke is a particular silhouette —
 * long and low, legs that look borrowed from a smaller dog, ears far too big
 * for the head, and a rounded rear with no tail at all. Get those four right
 * and it reads as a corgi at any size.
 *
 * Two things learned from the first attempt. Everything red is drawn in one
 * colour so overlapping shapes merge with no seams, and the white is a
 * *single* path running from the rear, along the belly, up to the chest —
 * drawn as separate pieces it read as a pompom stuck to a loaf of bread.
 *
 * He faces right, so he trots left to right and nothing is mirrored. The
 * four legs are groups with their own classes, drawn far pair first, so a
 * CSS leg cycle can swing them in opposite phase.
 */
export default function MontyBody({ size = 92 }: { size?: number }) {
  return (
    <svg
      className="dog" width={size * 1.5} height={size}
      viewBox="0 0 180 120" fill="none" xmlns="http://www.w3.org/2000/svg"
      role="img" aria-label="Monty, a corgi"
    >
      {/* far legs, darker so they sit behind. Capsules, not boxes: a square
          top shows as a hard edge wherever it crosses the belly. */}
      <g className="dog__leg dog__leg--backfar">
        <rect x="45" y="68" width="13" height="40" rx="6.5" fill="#B85E34" />
        <circle cx="51.5" cy="103" r="6.5" fill="#E7DCCE" />
      </g>
      <g className="dog__leg dog__leg--frontfar">
        <rect x="115" y="68" width="13" height="40" rx="6.5" fill="#B85E34" />
        <circle cx="121.5" cy="103" r="6.5" fill="#E7DCCE" />
      </g>

      {/* the whole dog in one colour — rump, back, neck and head together,
          so nothing shows a join */}
      <path
        d="M30 68c0-16 11-27 28-27h50c14 0 22 6 26 14 3 6 5 10 5 14 0 17-10 25-28 25H56C40 94 30 85 30 68z"
        fill="#D5713F"
      />
      <circle cx="56" cy="66" r="26" fill="#D5713F" />
      <circle cx="137" cy="47" r="27" fill="#D5713F" />
      {/* the chest, which the head and the body would otherwise leave a gap
          between. Without it the white below the muzzle has no red behind
          it and reads as a ball of fluff hung off the front of the dog. */}
      <circle cx="136" cy="70" r="22" fill="#D5713F" />

      {/* ears: the far one tucked behind, the near one forward */}
      <path d="M125 24c-4-13 0-22 5-23s9 8 10 20z" fill="#C06038" />
      <path d="M147 22c1-13 6-21 11-20s6 11 3 23z" fill="#D5713F" />
      <path d="M149 24c1-8 4-14 7-13s3 8 1 14z" fill="#F0C3A8" />

      {/* The white underside, as three soft ellipses rather than a path. Every
          version of this with straight runs in it read as a white box laid
          on the dog; curves only, and it reads as fur. Each one is kept
          inside the red behind it — white that spills past the silhouette
          stops being markings and becomes a shape of its own. */}
      <ellipse cx="100" cy="83" rx="42" ry="11" fill="#FBF6EE" />
      <ellipse cx="137" cy="74" rx="16" ry="15" fill="#FBF6EE" />
      <ellipse cx="54" cy="79" rx="16" ry="13" fill="#FBF6EE" />

      {/* blaze and muzzle */}
      <path d="M139 24c4 0 8 5 8 13s-4 12-8 12-7-4-7-12 3-13 7-13z" fill="#FBF6EE" />
      <ellipse cx="156" cy="56" rx="18" ry="13" fill="#FBF6EE" />

      {/* nose, eye, smile */}
      <ellipse cx="171" cy="53" rx="5" ry="4" fill="#2B2B2B" />
      <circle cx="142" cy="45" r="3.6" fill="#2B2B2B" />
      <circle cx="143.3" cy="43.7" r="1.3" fill="#FBF6EE" />
      <path d="M159 62c3 3 8 3 11 0" stroke="#2B2B2B" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M158 63c2 4 6 4 8 0z" fill="#E08E8E" />

      {/* near legs, over the chest. The capsule starts well up inside the
          body, so its top is never a line across the belly, and it is the
          same red as everything else, so the two merge. */}
      <g className="dog__leg dog__leg--back">
        <rect x="57" y="66" width="15" height="44" rx="7.5" fill="#D5713F" />
        <circle cx="64.5" cy="104" r="7.5" fill="#FBF6EE" />
      </g>
      <g className="dog__leg dog__leg--front">
        <rect x="127" y="66" width="15" height="44" rx="7.5" fill="#D5713F" />
        <circle cx="134.5" cy="104" r="7.5" fill="#FBF6EE" />
      </g>
    </svg>
  )
}
