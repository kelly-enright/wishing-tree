import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Check } from 'lucide-react'

/**
 * Short confirmations for the things that do not change the page.
 *
 * Granting a wish already answers itself with a whole screen; releasing a
 * pledge, or confirming a delivery window, used to change a line of text
 * somewhere below the fold and hope you noticed. Those get a toast.
 *
 * Deliberately not an error channel. Errors stay where the thing went wrong,
 * next to the control that failed, where they can be read at leisure and
 * acted on — a message about a failure that disappears after four seconds is
 * worse than no message.
 */

type Toast = { id: number; text: string }
const ToastContext = createContext<(text: string) => void>(() => {})

export function useToast() {
  return useContext(ToastContext)
}

export function ToastHost({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const show = useCallback((text: string) => {
    const id = Date.now() + Math.random()
    setToasts((all) => [...all, { id, text }])
    setTimeout(() => setToasts((all) => all.filter((t) => t.id !== id)), 4000)
  }, [])

  return (
    <ToastContext.Provider value={show}>
      {children}
      {/* `role="status"` rather than `alert`: these are confirmations, and a
          screen reader should finish its sentence before mentioning one. */}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <p key={toast.id} className="toast">
            <Check size={15} aria-hidden="true" />
            {toast.text}
          </p>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

/** Whether this reader has asked for less movement, kept current if they
 *  change the setting while the page is open. */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  useEffect(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  return reduced
}
