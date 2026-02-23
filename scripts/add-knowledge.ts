import { ConvexHttpClient } from 'convex/browser'

const convex = new ConvexHttpClient('https://impressive-panther-391.convex.cloud')

const beforestKnowledge = [
  {
    url: 'https://beforest.com/about',
    title: 'Who is Beforest?',
    content: 'Beforest Lifestyle Solutions creates regenerative living communities that heal the land while redefining how people live, work, and connect with nature.',
    summary: 'Introduction to Beforest',
  },
  {
    url: 'https://beforest.com/mission',
    title: 'Beforest Mission',
    content: 'Beforest designs and manages community-driven living landscapes that regenerate ecosystems and strengthen peoples connection with the land. Our approach blends ecological design, shared stewardship, and regenerative lifestyles.',
    summary: 'Beforest mission and approach',
  },
  {
    url: 'https://beforest.com/goal',
    title: 'Beforest Goals',
    content: 'By 2034, Beforest aims to create and support 10000 acres of collectives. By 2040, Beforest aims to restore over 1 million acres and inspire a movement of people to live regeneratively.',
    summary: 'Beforest 2040 goals',
  },
  {
    url: 'https://beforest.com/vision',
    title: 'Beforest Vision',
    content: 'To create landscapes that inspire and support life in all forms.',
    summary: 'Beforest vision statement',
  },
  {
    url: 'https://beforest.com/approach',
    title: 'Beforest Approach',
    content: 'Beforest applies the 4 Returns Framework: Return of Inspiration, Social Return, Natural Return, and Financial Return. Each collective becomes a living lab for regeneration.',
    summary: 'The 4 Returns Framework',
  },
  {
    url: 'https://beforest.com/what-we-do',
    title: 'What Beforest Does',
    content: 'Beforest builds regenerative living communities through: Ecological Design, Collective Ownership and Stewardship, Community Regeneration, and Regenerative Enterprises.',
    summary: 'Beforest services and offerings',
  },
  {
    url: 'https://beforest.com/impact',
    title: 'Beforest Impact',
    content: 'Impact areas: Restored Ecosystems, Regenerative Land Use, Thriving Communities, and Circular Economies.',
    summary: 'Beforest impact areas',
  },
  {
    url: 'https://beforest.com/principles',
    title: 'Beforest Core Principles',
    content: 'Beforest principles: Holistic, Inspiration-driven, Community-rooted, Collaborative, Long-term, Ecology-first, Learning-oriented, and Scalable.',
    summary: 'Beforest core principles',
  },
]

async function addKnowledgeItems() {
  for (const item of beforestKnowledge) {
    try {
      // @ts-ignore
      const result = await convex.mutation('chat:addKnowledgeItem', item)
      console.log('Added:', item.title, result)
    } catch (error) {
      console.error('Error adding:', item.title, error)
    }
  }
}

addKnowledgeItems()
