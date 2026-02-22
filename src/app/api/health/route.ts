export const runtime = 'nodejs'

export async function GET() {
  return Response.json({ status: 'ok', service: 'triggerdev-beforest' })
}

export async function POST() {
  return Response.json({ status: 'ok' })
}
