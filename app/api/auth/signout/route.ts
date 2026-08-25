import { NextResponse } from "next/server";
import { clearSession } from "@/lib/auth";
import { getConfig } from "@/lib/env";

export const runtime = "nodejs";

export async function POST() {
  await clearSession();
  return NextResponse.redirect(new URL("/", getConfig().APP_URL), { status: 303 });
}
