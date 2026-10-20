import { useEffect, useState } from 'react'
import { getActivity, type Activity,
  userMessage,
} from '../api'

/**
 * Every agent call, in order, with what it did and what it cost.
 *
 * No contact details can appear here. The summaries the server stores are
 * shape rather than content — an intake call records how long a family's
 * message was, never what it said — and the server scrubs everything again on
 * the way out.
 */
export default function AgentActivity({ token }: { token: string }) {
  const [data, setData] = useState<Activity | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getActivity(token).then(setData).catch((e) => setError(userMessage(e, 'We could not load the activity log.')))
  }, [token])

  if (error) return <p className="form__error">{error}</p>
  if (!data) return <p className="activity__loading">Loading agent activity…</p>

  const { totals, budget } = data
  const allInput = totals.input_tokens + totals.cached_input_tokens + (totals.cache_write_tokens ?? 0)
  const cachedShare = allInput > 0 ? Math.round((totals.cached_input_tokens / allInput) * 100) : 0

  return (
    <section className="activity">
      <div className="activity__totals">
        <div><span>Calls</span><strong>{totals.calls}</strong></div>
        <div><span>Input</span><strong>{totals.input_tokens.toLocaleString()}</strong></div>
        <div><span>Cached</span><strong>{totals.cached_input_tokens.toLocaleString()}</strong></div>
        <div><span>Cache write</span><strong>{(totals.cache_write_tokens ?? 0).toLocaleString()}</strong></div>
        <div><span>Output</span><strong>{totals.output_tokens.toLocaleString()}</strong></div>
        <div>
          <span>Cost</span>
          <strong>
            {totals.prices_are_placeholders ? 'price not set' : `$${totals.cost_usd.toFixed(5)}`}
          </strong>
        </div>
        <div>
          <span>Today’s budget</span>
          <strong>
            {budget.daily_tokens.toLocaleString()} / {budget.daily_cap.toLocaleString()}
          </strong>
        </div>
      </div>
      <p className="activity__note">
        {cachedShare}% of input tokens served from cache. No contact details are
        recorded on this page.
      </p>

      {data.calls.length === 0 && (
        <p className="activity__loading">No agent calls yet.</p>
      )}

      <ol className="activity__list">
        {data.calls.map((call, i) => (
          <li key={i} className={`call call--${call.agent}${call.ok ? '' : ' call--failed'}`}>
            <header className="call__head">
              <span className="call__agent">{call.agent}</span>
              <span className="call__op">{call.operation}</span>
              <span className="call__time">{call.timestamp.slice(11, 19)}</span>
            </header>

            <p className="call__io">
              <strong>In:</strong> {call.input_summary || '—'}<br />
              <strong>Out:</strong> {call.output_summary || '—'}
            </p>

            {call.tools_called.length > 0 && (
              <p className="call__tools">
                {call.tools_called.map((tool) => (
                  <span key={tool} className="chip">{tool}</span>
                ))}
              </p>
            )}

            {call.removed.length > 0 && (
              <p className="call__removed">
                <strong>Removed:</strong> {call.removed.join(', ')}
              </p>
            )}

            {call.flags.length > 0 && (
              <ul className="call__flags">
                {call.flags.map((flag, j) => (
                  <li key={j}><span className="chip chip--flag">{flag.kind}</span> {flag.reason}</li>
                ))}
              </ul>
            )}

            {call.enforced.length > 0 && (
              <ul className="call__enforced">
                {call.enforced.map((item, j) => (
                  <li key={j}>Code check: {item}</li>
                ))}
              </ul>
            )}

            {call.error && <p className="call__error">{call.error}</p>}

            <footer className="call__meta">
              {call.input_tokens.toLocaleString()} in · {call.cached_input_tokens.toLocaleString()} cached ·{' '}
              {call.output_tokens.toLocaleString()} out · {call.latency_ms} ms
              {call.prompt_version && ` · prompt ${call.prompt_version}`}
            </footer>
          </li>
        ))}
      </ol>
    </section>
  )
}
