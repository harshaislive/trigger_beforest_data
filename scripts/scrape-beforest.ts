import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://impressive-panther-391.convex.cloud')

const sitemapUrl = 'https://beforest.co/wp-sitemap-posts-page-1.xml'

async function getPagesFromSitemap(): Promise<{ url: string; title: string }[]> {
  const response = await fetch(sitemapUrl)
  const xml = await response.text()
  
  const urlMatches = xml.match(/<loc>(.*?)<\/loc>/g) || []
  
  const pages: { url: string; title: string }[] = []
  
  for (const match of urlMatches) {
    const url = match.replace(/<\/?loc>/g, '')
    
    if (url.includes('/sitemap') || 
        url.includes('/feed') || 
        url.includes('tag=') || 
        url.includes('category=') ||
        url.includes('?') ||
        url.includes('brochure') ||
        url.includes('thank-you') ||
        url.includes('temp') ||
        url.includes('bebuilder') ||
        url.includes('virtual-office') ||
        url.includes('payments') ||
        url.includes('planter') ||
        url.includes('shipping') ||
        url.includes('my-temp') ||
        url.includes('cupping') ||
        url.includes('wilderness-collectivess') ||
        url.includes('awaken') ||
        url.includes('yoga') ||
        url.includes('astro') ||
        url.includes('letter') ||
        url.includes('fold')) {
      continue
    }
    
    let title = url.replace('https://beforest.co/', '').replace(/\/$/, '').replace(/-/g, ' ')
    title = title.charAt(0).toUpperCase() + title.slice(1)
    
    pages.push({ url, title })
  }
  
  return pages
}

async function scrapePage(url: string): Promise<string> {
  const response = await fetch(url)
  const html = await response.text()
  
  return html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<header[^>]*>[\s\S]*?<\/header>/gi, '')
    .replace(/<footer[^>]*>[\s\S]*?<\/footer>/gi, '')
    .replace(/<nav[^>]*>[\s\S]*?<\/nav>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 4000)
}

async function scrapeAndAdd() {
  const pages = await getPagesFromSitemap()
  console.log(`Found ${pages.length} pages`)
  
  let count = 0
  for (const page of pages) {
    try {
      const content = await scrapePage(page.url)
      // @ts-ignore
      await convex.mutation('chat:addKnowledgeItem', {
        url: page.url,
        title: page.title,
        content,
        summary: `Beforest ${page.title}`,
      })
      count++
      console.log(`Added (${count}/${pages.length}): ${page.title}`)
    } catch (error) {
      console.error(`Error: ${page.title}`, error)
    }
  }
  
  console.log(`Done! Added ${count} pages.`)
}

scrapeAndAdd()
