import { useEffect } from 'react'

/**
 * Adds a class to `<body>` for as long as a page is open.
 *
 * The landing and About pages want a warm glow spanning the whole window.
 * Painting it on the page element does not work: that element is a centred
 * column, so the glow stops at its edge and leaves a visible rectangle. And
 * drawing it as an absolutely positioned child wide enough to look like
 * light makes the page scroll sideways.
 *
 * The body is the only box that is reliably the size of the window, so the
 * glow goes there and leaves when the page does.
 */
export default function useBodyClass(name: string) {
  useEffect(() => {
    document.body.classList.add(name)
    return () => document.body.classList.remove(name)
  }, [name])
}
