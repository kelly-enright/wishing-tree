import { ExternalLink, MapPin } from 'lucide-react'

/**
 * Links a wish granter can act on: the product page, and the hub on a map.
 *
 * Only allowlisted retailers ever reach a wish card — `config.is_allowed_retailer`
 * decides that on the server, and a link that fails is never stored — so by the
 * time one arrives here it is safe to show. Both open in a new tab, because
 * losing a half-filled grant form to a trip to Target is a bad trade.
 *
 * `rel="noreferrer"` matters: without it the store page can reach back through
 * `window.opener`, and it would also learn which page sent them.
 */

export function ItemLink({ href, small = false }: { href: string; small?: boolean }) {
  return (
    <a
      className={`btn btn--light${small ? ' btn--small' : ''} itemlink`}
      href={href} target="_blank" rel="noreferrer noopener"
    >
      <ExternalLink size={small ? 13 : 15} aria-hidden="true" />
      View item
    </a>
  )
}

export function MapLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a className="maplink" href={href} target="_blank" rel="noreferrer noopener">
      <MapPin size={13} aria-hidden="true" />
      {children}
    </a>
  )
}
