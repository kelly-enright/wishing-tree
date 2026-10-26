import { useEffect } from 'react'
import { useLocation, useNavigationType } from 'react-router-dom'

/**
 * A new page starts at the top.
 *
 * React Router leaves the window exactly where it was when the route
 * changes, so following a link from halfway down one page opened the next
 * one halfway down as well — the page looked like it had loaded wrong.
 *
 * Back and forward are left alone. A POP means the person is returning to
 * something they have already read, and putting them back where they left
 * it is the behavior every browser has taught them to expect.
 *
 * Renders nothing; it only has an effect.
 */
export default function ScrollToTop() {
  const { pathname, hash } = useLocation()
  const navigationType = useNavigationType()

  useEffect(() => {
    if (navigationType === 'POP') return

    if (hash) {
      // Somebody asked for a specific place on the page, so honor it.
      document.getElementById(hash.slice(1))?.scrollIntoView()
      return
    }

    // 'instant' rather than the default: a page that animates its way to the
    // top on arrival reads as a glitch, and it fights reduced motion.
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' as ScrollBehavior })
  }, [pathname, hash, navigationType])

  return null
}
