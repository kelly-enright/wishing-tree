import type { Usage } from '../api'

/** What this intake has cost so far, in tokens and dollars. */
export default function TokenPanel({ usage }: { usage: Usage | null }) {
  if (!usage) return null

  const total = usage.input_tokens + usage.cached_input_tokens + usage.output_tokens
  const cachedShare = total > 0 ? Math.round((usage.cached_input_tokens / total) * 100) : 0

  return (
    <aside className="tokens" aria-label="Token usage for this session">
      <h2 className="tokens__title">This session</h2>
      <dl className="tokens__grid">
        <div><dt>Calls</dt><dd>{usage.calls}</dd></div>
        <div><dt>Input</dt><dd>{usage.input_tokens.toLocaleString()}</dd></div>
        <div><dt>Cached input</dt><dd>{usage.cached_input_tokens.toLocaleString()}</dd></div>
        <div><dt>Output</dt><dd>{usage.output_tokens.toLocaleString()}</dd></div>
        <div><dt>Total</dt><dd>{total.toLocaleString()}</dd></div>
        <div>
          <dt>Cost</dt>
          <dd>
            {usage.prices_are_placeholders
              ? <span className="tokens__pending">price not set</span>
              : `$${usage.cost_usd.toFixed(4)}`}
          </dd>
        </div>
      </dl>
      <p className="tokens__note">
        {cachedShare}% of input was served from cache · {usage.model}
      </p>
    </aside>
  )
}
