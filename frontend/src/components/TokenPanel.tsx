import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { Usage } from '../api'

/**
 * What this session has cost so far, in tokens and dollars.
 *
 * `open` decides whether it starts expanded. On Admin and the agent activity
 * page it does, because that is the job. For a neighbor or a wish granter it
 * starts shut behind "Show AI details": someone asking for a winter coat does
 * not need cache-write counts beside their wishes, and a dollar figure next
 * to a request for help reads strangely. It is one click away rather than
 * gone, because what the agents cost is worth being able to see.
 */
export default function TokenPanel({
  usage, open = false,
}: { usage: Usage | null; open?: boolean }) {
  const [shown, setShown] = useState(open)
  if (!usage) return null

  const allInput = usage.input_tokens + usage.cached_input_tokens + usage.cache_write_tokens
  const total = allInput + usage.output_tokens
  const cachedShare = allInput > 0 ? Math.round((usage.cached_input_tokens / allInput) * 100) : 0

  return (
    <aside className="tokens" aria-label="Token usage for this session">
      {open ? (
        <h2 className="tokens__title">This session</h2>
      ) : (
        <button
          type="button"
          className={`tokens__toggle${shown ? ' tokens__toggle--open' : ''}`}
          aria-expanded={shown}
          onClick={() => setShown((was) => !was)}
        >
          <ChevronDown size={14} aria-hidden="true" />
          Show AI details
        </button>
      )}

      {!shown ? null : (
      <>
      <dl className="tokens__grid">
        <div><dt>Calls</dt><dd>{usage.calls}</dd></div>
        <div><dt>Input</dt><dd>{usage.input_tokens.toLocaleString()}</dd></div>
        <div><dt>Cached input</dt><dd>{usage.cached_input_tokens.toLocaleString()}</dd></div>
        <div><dt>Cache write</dt><dd>{usage.cache_write_tokens.toLocaleString()}</dd></div>
        <div><dt>Output</dt><dd>{usage.output_tokens.toLocaleString()}</dd></div>
        <div><dt>Total</dt><dd>{total.toLocaleString()}</dd></div>
        <div>
          <dt>Cost</dt>
          <dd>
            {usage.prices_are_placeholders
              ? <span className="tokens__pending">price not set</span>
              : `$${usage.cost_usd.toFixed(5)}`}
          </dd>
        </div>
      </dl>
      <p className="tokens__note">
        {cachedShare}% of input was served from cache · {usage.model}
      </p>
      </>
      )}
    </aside>
  )
}
