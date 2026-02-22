import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Trigger.dev Knowledge Chatbot',
  description: 'AI-powered knowledge base chatbot',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
