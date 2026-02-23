import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://impressive-panther-391.convex.cloud')

const pages = [
  { url: 'https://beforest.co/', title: 'Home' },
  { url: 'https://beforest.co/about-us/', title: 'About Us' },
  { url: 'https://beforest.co/farming-collectives/', title: 'What is a Collective' },
  { url: 'https://beforest.co/the-poomaale-estate/', title: 'Poomaale 1.0' },
  { url: 'https://beforest.co/poomaale-2-0-collective/', title: 'Poomaale 2.0' },
  { url: 'https://beforest.co/hyderabad-collective/', title: 'Hyderabad Collective' },
  { url: 'https://beforest.co/the-mumbai-collective/', title: 'Mumbai Collective' },
  { url: 'https://beforest.co/the-bhopal-collective/', title: 'Bhopal Collective' },
  { url: 'https://beforest.co/co-forest/', title: 'Co-Forest (Hammiyala)' },
  { url: 'https://beforest.co/contact-us/', title: 'Contact' },
  { url: 'https://beforest.co/careers/', title: 'Careers' },
  { url: 'https://beforest.co/faq/', title: 'FAQ' },
]

async function scrapeAndAdd() {
  for (const page of pages) {
    try {
      console.log(`Scraping: ${page.url}`)
      
      const response = await fetch(page.url)
      const html = await response.text()
      
      // Extract text content (simple approach - remove HTML tags)
      const text = html
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
        .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
        .replace(/<[^>]+>/g, ' ')
        .replace(/\s+/g, ' ')
        .trim()
      
      // Extract main content (first 3000 chars of meaningful text)
      const content = text.slice(0, 3000)
      
      // Add to Convex
      // @ts-ignore
      await convex.mutation('chat:addKnowledgeItem', {
        url: page.url,
        title: page.title,
        content: content,
        summary: `Beforest ${page.title} page`,
      })
      
      console.log(`Added: ${page.title}`)
    } catch (error) {
      console.error(`Error with ${page.url}:`, error)
    }
  }
  
  console.log('Done scraping!')
}

scrapeAndAdd()
