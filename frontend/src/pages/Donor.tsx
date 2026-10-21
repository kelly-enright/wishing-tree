import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  CATEGORY_LABELS, OCCASION_LABELS, getGranted, getWishes, requestMatches,
  type Category, type GrantResponse, type Match, type Occasion,
  type RegionInfo, type Usage, type WallFilters, type WishCard as Wish,
  userMessage,
} from '../api'
import DonorHowItWorks from '../components/DonorHowItWorks'
import HowItArrives from '../components/HowItArrives'
import Collapsible from '../components/Collapsible'
import Thinking from '../components/Thinking'
import TokenPanel from '../components/TokenPanel'
import WishCard from '../components/WishCard'
import WishTree from '../components/WishTree'
import { WishPanel, WishSheet, useNarrow } from '../components/WishOpen'
import Monty, { MontySays } from '../components/Monty'
import GrantConfirm from './GrantConfirm'
import MyGranted from './MyGranted'
import { useSession } from '../session'
import NeedsSignIn, { PageLoading } from '../components/NeedsSignIn'
import { signOut, switchSide } from '../auth'
import { MapLink } from '../components/ItemLink'
import { MontySparkles } from '../components/MontySparkles'
import { longDay, when } from '../dates'
import TopBar from '../components/TopBar'
import { useToast } from '../components/Toast'
import { TreePine, HeartHandshake, Info, SlidersHorizontal } from 'lucide-react'
import CategoryIcon from '../components/CategoryIcon'
import usePageTitle from '../usePageTitle'
import { SkeletonGrid } from '../components/Skeleton'

const EMPTY: WallFilters = { categories: [], occasion: '', requestType: '', maxCost: '' }

/** The same plain maps search the server builds, for payloads that carry
 *  only the address. No API key, opens whatever maps app the device has. */
function mapsUrl(address: string): string {
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(address)
}

export default function Donor() {
  usePageTitle('The Wish Tree')
  const { session, me, loading } = useSession()
  const toast = useToast()
  const location = useLocation()
  const navigate = useNavigate()
  const [filters, setFilters] = useState<WallFilters>(EMPTY)
  const [wishes, setWishes] = useState<Wish[]>([])
  const [region, setRegion] = useState<RegionInfo | null>(null)
  const [matches, setMatches] = useState<Match[] | null>(null)
  const [note, setNote] = useState('')
  const [usage, setUsage] = useState<Usage | null>(null)
  const [granted, setGranted] = useState<GrantResponse | null>(null)
  const [confirming, setConfirming] = useState<Wish | null>(null)
  const [view, setView] = useState<'tree' | 'list'>('tree')
  // Two halves of a granter's job: finding a wish, and keeping the promises
  // already made. They were one long scroll; they are tabs now.
  const [tab, setTab] = useState<'tree' | 'mine'>('tree')
  const [moreFilters, setMoreFilters] = useState(false)
  const [comingUp, setComingUp] = useState(0)
  const [gold, setGold] = useState<{ id: number; category: Category }[]>([])
  const [goldDays, setGoldDays] = useState(30)
  const [busy, setBusy] = useState<'wall' | 'match' | number | null>('wall')
  const [error, setError] = useState<string | null>(null)
  // The wish a tapped leaf opened. It lives here rather than in the tree
  // because it is drawn outside the tree — in the panel beside it on a wide
  // screen, in a sheet over it on a phone.
  const [openWish, setOpenWish] = useState<Wish | null>(null)
  const narrow = useNarrow(900)

  function loadWall(next: WallFilters) {
    setBusy('wall')
    setError(null)
    getWishes(next)
      .then((wall) => {
        setWishes(wall.wishes)
        setRegion(wall.region)
        setGold(wall.recently_granted ?? [])
        setGoldDays(wall.granted_window_days ?? 30)
      })
      .catch((e) => setError(userMessage(e, 'We could not load the tree.')))
      .finally(() => setBusy(null))
  }

  useEffect(() => { loadWall(EMPTY) }, [])

  /**
   * Arriving with `?wish=` — somebody who tapped that leaf on the landing
   * page before they had an account. Open its confirmation as soon as the
   * tree has loaded, so they finish the thing they came to do.
   *
   * The id is dropped from the URL afterwards, so a refresh or a back button
   * does not reopen a wish they have already dealt with.
   */
  useEffect(() => {
    const wanted = Number(new URLSearchParams(location.search).get('wish'))
    if (!wanted || wishes.length === 0) return
    const found = wishes.find((w) => w.id === wanted)
    if (found) setConfirming(found)
    else setNote("That wish has been granted by someone else. Here's the rest of the tree.")
    navigate('/donor', { replace: true })
  }, [wishes, location.search, navigate])

  // The badge on the tab, kept current when a grant or a release changes it.
  useEffect(() => {
    if (!session) return
    getGranted(session.alias)
      .then((data) => setComingUp(data.coming_up.length))
      .catch(() => setComingUp(0))
  }, [session?.alias, granted, tab])

  if (loading) return <PageLoading />
  if (!session || session.role !== 'donor') {
    return <NeedsSignIn want="donor" />
  }

  function update(patch: Partial<WallFilters>) {
    const next = { ...filters, ...patch }
    setFilters(next)
    setMatches(null)
    loadWall(next)
  }

  function toggleCategory(category: Category) {
    update({
      categories: filters.categories.includes(category)
        ? filters.categories.filter((c) => c !== category)
        : [...filters.categories, category],
    })
  }

  async function match() {
    setBusy('match')
    setError(null)
    try {
      const result = await requestMatches(session!.alias, filters)
      setMatches(result.matches)
      setNote(result.note)
      setUsage(result.usage)
    } catch (e) {
      setError(userMessage(e, 'We could not fetch your matches just now. Please try again.'))
    } finally {
      setBusy(null)
    }
  }

  function openConfirmation(wish: Wish) {
    setError(null)
    setConfirming(wish)
  }

  if (confirming) {
    return (
      <main className="page page--wide">
        <TopBar
          links={[]} alias={session.alias} me={me}
          onSwitch={signOut} onSwitchSide={switchSide}
        />
        <GrantConfirm
          wish={confirming}
          donorAlias={session.alias}
          onGranted={(result) => {
            setConfirming(null)
            setGranted(result)
            // The thank-you screen says what it meant; the toast says where
            // the wish went, which is the question right after "thank you".
            toast('Added to your Coming up list')
          }}
          onCancel={() => { setConfirming(null); loadWall(filters); setMatches(null) }}
        />
      </main>
    )
  }

  if (granted) {
    const { logistics } = granted
    return (
      <main className="page">
        <TopBar
          links={[]} alias={session.alias} me={me}
          onSwitch={signOut} onSwitchSide={switchSide}
        />
        <div className="thanks">
          <MontySparkles size={84} replay={granted.wish.id} />
          <h1 className="page__title">You just made a neighbor's week. Thank you.</h1>
        </div>
        <p className="page__blurb">{granted.wish.item_description}</p>

        <section className={`logistics logistics--${logistics.kind}`}>
          <h2 className="logistics__headline">{logistics.headline}</h2>
          {logistics.kind === 'hub_dropoff' ? (
            <dl className="logistics__facts">
              <div><dt>Where</dt><dd>
                {logistics.hub_name}<br />
                <MapLink href={mapsUrl(logistics.hub_address)}>{logistics.hub_address}</MapLink>
              </dd></div>
              <div><dt>Drop off on</dt>
                <dd>{when(logistics.dropoff_date, logistics.dropoff_window)}</dd></div>
              <div><dt>Delivered</dt>
                <dd>{when(logistics.delivery_date, logistics.delivery_window)}</dd></div>
            </dl>
          ) : (
            <>
              <p className="logistics__detail">{logistics.detail}</p>
              <p className="logistics__detail">Paid on {longDay(logistics.delivery_date)}.</p>
            </>
          )}
          {!granted.arrives_in_time && (
            <p className="logistics__late">{granted.schedule_note}</p>
          )}
          {logistics.kind === 'hub_dropoff' && (
            <p className="logistics__detail">
              Feel free to include a handwritten card. We'll pass it along with
              your gift.
            </p>
          )}
        </section>

        <button
          type="button" className="btn btn--light"
          onClick={() => { setGranted(null); loadWall(filters); setMatches(null) }}
        >
          Back to the tree
        </button>
      </main>
    )
  }

  const showing = matches ? matches.map((m) => m.wish) : wishes
  // How many of the tucked-away filters are actually doing something, so the
  // button can say so rather than hiding the fact that the tree is narrowed.
  const extraCount =
    (filters.occasion ? 1 : 0) + (filters.requestType ? 1 : 0) + (filters.maxCost ? 1 : 0)

  const nav = [
    {
      label: 'Wish Tree', short: 'Tree',
      icon: <TreePine size={17} aria-hidden="true" />,
      onClick: () => setTab('tree'), active: tab === 'tree',
    },
    {
      label: "Wishes I'm granting", short: 'Granting',
      icon: <HeartHandshake size={17} aria-hidden="true" />,
      onClick: () => setTab('mine'), active: tab === 'mine',
      // Only what is still to do. Finished wishes are not a to-do list.
      count: comingUp || undefined,
    },
    {
      label: 'About', short: 'About',
      icon: <Info size={17} aria-hidden="true" />, to: '/about',
    },
  ]

  return (
    <main className="page page--wide">
      <TopBar
        links={nav} alias={session.alias} me={me}
        onSwitch={signOut} onSwitchSide={switchSide}
      />

      {tab === 'mine' && <MyGranted alias={session.alias} />}

      {tab === 'tree' && (
      <>
      <div className="donorhead">
        <h1 className="page__title">The Wish Tree</h1>
        <div className="viewtoggle" role="group" aria-label="How to see the wishes">
          <button
            type="button" className={`viewtoggle__btn${view === 'tree' ? ' viewtoggle__btn--on' : ''}`}
            onClick={() => setView('tree')} aria-pressed={view === 'tree'}
          >
            Tree
          </button>
          <button
            type="button" className={`viewtoggle__btn${view === 'list' ? ' viewtoggle__btn--on' : ''}`}
            onClick={() => setView('list')} aria-pressed={view === 'list'}
          >
            See as a list
          </button>
        </div>
      </div>

      <section className="filters" aria-label="Filter the wishes">
        <p className="filters__how">
          Filters narrow the tree to the wishes you want to see. <strong>Match
          me to wishes</strong> reads your budget and the things you like to
          help with, and picks a few it thinks fit you best.
        </p>

        {/* One row that scrolls sideways, so seven categories do not become
            three lines of buttons on a phone. Icons carry the meaning at a
            glance; the words are still there for everyone else. */}
        <div
          className="chiprow" role="group" aria-label="Categories"
          ref={(node) => {
            // Drop the fade once the row is scrolled to its end, so the last
            // chip is never left looking half-disabled.
            if (!node) return
            const sync = () => node.classList.toggle(
              'chiprow--end',
              node.scrollLeft + node.clientWidth >= node.scrollWidth - 2,
            )
            sync()
            node.addEventListener('scroll', sync, { passive: true })
          }}
        >
          {(Object.keys(CATEGORY_LABELS) as Category[]).map((category) => (
            <button
              key={category} type="button"
              className={`chip${filters.categories.includes(category) ? ' chip--on' : ''}`}
              aria-pressed={filters.categories.includes(category)}
              onClick={() => toggleCategory(category)}
            >
              <CategoryIcon category={category} size={14} />
              {CATEGORY_LABELS[category]}
            </button>
          ))}
        </div>

        <div className="filters__row filters__row--inputs">
          <button
            type="button"
            className={`btn btn--light btn--small morefilters${extraCount ? ' morefilters--on' : ''}`}
            aria-expanded={moreFilters}
            onClick={() => setMoreFilters((was) => !was)}
          >
            <SlidersHorizontal size={14} aria-hidden="true" />
            More filters
            {extraCount > 0 && <span className="morefilters__count">{extraCount}</span>}
          </button>

          <button
            type="button" className="btn btn--primary"
            onClick={match} disabled={busy === 'match'}
          >
            {busy === 'match' ? 'Matching…' : 'Match me to wishes'}
          </button>

          {matches && (
            <button type="button" className="btn btn--light" onClick={() => setMatches(null)}>
              Show the whole tree
            </button>
          )}
        </div>

        {moreFilters && (
        <div className="filters__row filters__row--inputs filters__more">
          <label className="field field--inline">
            <span className="field__label">Occasion</span>
            <select
              className="field__input" value={filters.occasion}
              onChange={(e) => update({ occasion: e.target.value as Occasion | '' })}
            >
              <option value="">Any</option>
              {(Object.keys(OCCASION_LABELS) as Occasion[]).map((o) => (
                <option key={o} value={o}>{OCCASION_LABELS[o]}</option>
              ))}
            </select>
          </label>

          <label className="field field--inline">
            <span className="field__label">Type</span>
            <select
              className="field__input" value={filters.requestType}
              onChange={(e) => update({ requestType: e.target.value as 'specific' | 'flexible' | '' })}
            >
              <option value="">Any</option>
              <option value="specific">Specific item</option>
              <option value="flexible">Flexible need</option>
            </select>
          </label>

          <label className="field field--inline">
            <span className="field__label">Up to ($)</span>
            <input
              className="field__input" type="number" min="0" step="10"
              value={filters.maxCost} placeholder="any"
              onChange={(e) => update({ maxCost: e.target.value })}
            />
          </label>

          {extraCount > 0 && (
            <button
              type="button" className="btn btn--ghost btn--small"
              onClick={() => update({ occasion: '', requestType: '', maxCost: '' })}
            >
              Clear
            </button>
          )}
        </div>
        )}
      </section>

      {error && <p className="form__error" role="alert">{error}</p>}

      {busy === 'match' && (
        <Thinking label="Monty is sniffing out wishes that fit you" />
      )}

      {matches && (
        <div className="matchbar">
          <strong>{matches.length} match{matches.length === 1 ? '' : 'es'}</strong> ranked for you
          {note && <span className="matchbar__note"> — {note}</span>}
        </div>
      )}

      {/* On a phone there is no room beside the tree, so "How it works" sits
          above it as one folded line. On a wide screen it lives in the panel
          to the right instead, and nothing stands between the filters and
          the tree. */}
      {narrow && !matches && (
        <Collapsible id="donor-how" title="How it works" defaultOpen={false}>
          <DonorHowItWorks compact />
        </Collapsible>
      )}

      <div className="wall">
        <div className="wall__cards">
          {view === 'tree' && busy !== 'wall' && (
            <WishTree
              wishes={showing}
              granted={matches ? [] : gold}
              grantedWindowDays={goldDays}
              onSeeList={() => setView('list')}
              selectedId={openWish?.id ?? null}
              onSelect={setOpenWish}
            />
          )}

          {view === 'tree' && busy !== 'wall' && showing.length === 0 && (
            <MontySays>
              Nothing matches those filters today. Monty says try taking one off —
              new wishes go up every week.
            </MontySays>
          )}

          {view === 'list' && busy === 'wall' && (
            <>
              <p className="sr-only" role="status">Loading wishes…</p>
              <SkeletonGrid count={4} />
            </>
          )}
          {view === 'list' && busy !== 'wall' && showing.length === 0 && (
            <div className="wall__empty">
              <Monty size={64} />
              <p className="wall__empty-title">Nothing here right now</p>
              <p>
                {matches
                  ? "Nothing fits those filters today. Monty suggests widening them, or looking at the whole tree."
                  : 'No open wishes match those filters today. Try removing a filter — new wishes go up every week.'}
              </p>
            </div>
          )}
          {view === 'list' && showing.map((wish) => (
            <WishCard
              key={wish.id}
              wish={wish}
              reason={matches?.find((m) => m.request_id === wish.id)?.reason}
              onGrant={openConfirmation}
              granting={busy === wish.id}
            />
          ))}
        </div>

        <div className="wall__side">
          {matches && <TokenPanel usage={usage} />}

          {/* One panel, two jobs. With nothing open it explains the place;
              tap a leaf and the wish takes it over, so the answer appears
              where the question was asked and the tree never moves. */}
          {!narrow && openWish ? (
            <WishPanel
              wish={openWish}
              reason={matches?.find((m) => m.request_id === openWish.id)?.reason}
              onGrant={openConfirmation}
              granting={busy === openWish.id}
              onClose={() => setOpenWish(null)}
            />
          ) : (
            <>
              {/* Not on a phone: there it is the folded line above the tree,
                  and saying it twice on one screen is worse than not at all. */}
              {!narrow && !matches && <DonorHowItWorks compact />}
              {region && <HowItArrives region={region} />}
            </>
          )}
        </div>
      </div>

      {narrow && openWish && (
        <WishSheet
          wish={openWish}
          reason={matches?.find((m) => m.request_id === openWish.id)?.reason}
          onGrant={openConfirmation}
          granting={busy === openWish.id}
          onClose={() => setOpenWish(null)}
        />
      )}
      </>
      )}
    </main>
  )
}
