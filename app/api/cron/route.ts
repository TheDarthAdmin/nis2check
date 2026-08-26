import { NextRequest, NextResponse } from "next/server";
import { HostedApiError, startScheduledRuns } from "@/lib/hosted-api";

export const runtime = "nodejs";
export const maxDuration = 300;

export async function GET(request: NextRequest) {
  if (!process.env.CRON_SECRET || request.headers.get("authorization") !== `Bearer ${process.env.CRON_SECRET}`) return NextResponse.json({ detail: "Unauthorized." }, { status: 401 });
  try {
    return NextResponse.json(await startScheduledRuns());
  } catch (error) {
    const detail = error instanceof HostedApiError ? error.message : "Unable to start scheduled collection.";
    return NextResponse.json({ detail }, { status: 503 });
  }
}
