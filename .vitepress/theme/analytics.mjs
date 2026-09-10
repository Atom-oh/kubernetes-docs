export const GA_ID = 'G-GWVLEW5JLL'

function pageUrl(value) {
  const url = new URL(value)
  url.hash = ''
  return url
}

// Keep GA4's automatic page_view measurement intact. A separate event gives
// documentation-specific counts without duplicating enhanced measurement.
export function createDocViewTracker(initialReferrer, send) {
  let previous
  return (location, title) => {
    const current = pageUrl(location)
    if (current.href === previous?.href) return
    send('event', 'docs_page_view', {
      send_to: GA_ID,
      page_location: current.href,
      page_path: current.pathname + current.search,
      page_title: title,
      page_referrer: previous?.href ?? initialReferrer
    })
    previous = current
  }
}
