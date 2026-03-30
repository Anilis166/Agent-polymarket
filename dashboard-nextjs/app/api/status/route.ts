import { NextResponse } from "next/server";

const BOT_SERVER = process.env.BOT_SERVER_URL ?? "http://localhost:8080";

export async function GET() {
  try {
    const res = await fetch(`${BOT_SERVER}/api/status`, {
      next: { revalidate: 0 },
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) throw new Error(`upstream ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { error: "Bot server unreachable", detail: String(e) },
      { status: 503 }
    );
  }
}
