import { useEffect, useState } from 'react'

/**
 * Shown whenever an agent is working.
 *
 * Model calls on this endpoint are usually quick but occasionally are not —
 * the slowest measured during development was 87 seconds. After ten seconds
 * this says so, because a spinner that never changes reads as a frozen app,
 * and someone waiting on help should not have to wonder whether it broke.
 */
export default function Thinking({
  label = 'Thinking', slowAfterMs = 10000,
}: { label?: string; slowAfterMs?: number }) {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), slowAfterMs)
    return () => clearTimeout(timer)
  }, [slowAfterMs])

  return (
    <div className="thinking" role="status" aria-live="polite">
      <span className="thinking__dots" aria-hidden="true">
        <i /><i /><i />
      </span>
      <span className="thinking__label">
        {label}
        {slow && (
          <span className="thinking__slow">
            {' '}— this one is taking a little longer than usual. Nothing has gone
            wrong, and your answers are safe.
          </span>
        )}
      </span>
    </div>
  )
}
