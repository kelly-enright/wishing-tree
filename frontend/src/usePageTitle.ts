import { useEffect } from 'react'

/**
 * The browser tab's title, per screen.
 *
 * Every page used to be "Wishing Tree", which makes a pinned tab useless and
 * a browser history unreadable. The site name stays on the end, the way a
 * newspaper puts its masthead after the headline.
 */
export default function usePageTitle(title?: string) {
  useEffect(() => {
    document.title = title ? `${title} · Wishing Tree` : 'Wishing Tree'
    return () => { document.title = 'Wishing Tree' }
  }, [title])
}
