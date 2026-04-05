import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Nara OTC — Peer-to-Peer NARA Trading',
  description: 'Buy and sell NARA tokens securely via OTC marketplace',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
