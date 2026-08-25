import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { HostedApiError, startHostedRun } from "@/lib/hosted-api";

export const runtime = "nodejs";
export const maxDuration = 300;

export async function POST() {
  if (!(await getSession())) return NextResponse.json({ detail: "Sign in required." }, { status: 401 });
  try {
    return NextResponse.json(await startHostedRun());
  } catch (error) {
    const detail = error instanceof HostedApiError ? error.message : "Unable to start collection.";
    return NextResponse.json({ detail }, { status: 503 });
  }
}
