import { NextRequest, NextResponse } from "next/server";
import { consumeAdminConsentTransaction } from "@/lib/admin-consent-transaction";
import { getSession } from "@/lib/auth";
import { getConfig } from "@/lib/env";
import { completeTenantOnboarding } from "@/lib/hosted-api";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const config = getConfig();
  const transaction = await consumeAdminConsentTransaction();
  const session = await getSession();
  const state = request.nextUrl.searchParams.get("state");
  const tenant = request.nextUrl.searchParams.get("tenant")?.toLowerCase();
  const consented = request.nextUrl.searchParams.get("admin_consent") === "True";

  if (
    !transaction ||
    !session ||
    !consented ||
    state !== transaction.state ||
    tenant !== transaction.tenantId.toLowerCase() ||
    session.tenantId.toLowerCase() !== transaction.tenantId.toLowerCase()
  ) {
    return NextResponse.redirect(new URL("/runs/latest?onboarding=failed", config.APP_URL));
  }

  try {
    await completeTenantOnboarding(transaction.tenantId);
    return NextResponse.redirect(new URL("/runs/latest?onboarding=complete", config.APP_URL));
  } catch {
    return NextResponse.redirect(new URL("/runs/latest?onboarding=failed", config.APP_URL));
  }
}
