import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { HostedApiError, saveTenantProfile } from "@/lib/hosted-api";
import { ScopingDeclaration } from "@/lib/types";

export const runtime = "nodejs";

/** Stores what the organisation declares about itself. Nothing here is read from the tenant. */
export async function PUT(request: Request) {
  const session = await getSession();
  if (!session) return NextResponse.json({ detail: "Sign in required." }, { status: 401 });
  let declared: Partial<ScopingDeclaration>;
  try {
    declared = (await request.json()) as Partial<ScopingDeclaration>;
  } catch {
    return NextResponse.json({ detail: "Send the declaration as JSON." }, { status: 400 });
  }
  if (!declared.sectorKey) return NextResponse.json({ detail: "Choose an activity first." }, { status: 400 });
  try {
    return NextResponse.json(await saveTenantProfile(session.tenantId, declared));
  } catch (error) {
    const detail = error instanceof HostedApiError ? error.message : "The declaration could not be saved.";
    return NextResponse.json({ detail }, { status: error instanceof HostedApiError ? error.status || 503 : 503 });
  }
}
