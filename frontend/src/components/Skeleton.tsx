/**
 * Placeholder shapes for the moment before data arrives.
 *
 * The point is not decoration: a blank area reads as "nothing here", while
 * shapes the size of the coming content read as "nearly there", and the page
 * does not jump when the real thing lands.
 *
 * `aria-hidden` throughout, with the live region left to say "Loading…" once,
 * because a screen reader has no use for eleven grey rectangles.
 */

export function SkeletonCard() {
  return (
    <article className="card card--ghost" aria-hidden="true">
      <div className="skeleton" style={{ height: 13, width: '38%' }} />
      <div className="skeleton" style={{ height: 17, width: '86%', marginTop: 12 }} />
      <div className="skeleton" style={{ height: 17, width: '62%', marginTop: 6 }} />
      <div className="skeleton" style={{ height: 34, width: '100%', marginTop: 16 }} />
      <div className="skeleton" style={{ height: 36, width: '100%', marginTop: 14 }} />
    </article>
  )
}

export function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="card card--ghost" style={{ marginBottom: 12 }}>
          <div className="skeleton" style={{ height: 13, width: '30%' }} />
          <div className="skeleton" style={{ height: 16, width: '72%', marginTop: 10 }} />
          <div className="skeleton" style={{ height: 13, width: '48%', marginTop: 8 }} />
        </div>
      ))}
    </div>
  )
}

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => <SkeletonCard key={i} />)}
    </>
  )
}
