import { NextResponse } from "next/server";
import { startAdminConsentTransaction } from "@/lib/admin-consent-transaction";
import { getSession } from "@/lib/auth";
import { getConfig } from "@/lib/env";

export const runtime = "nodejs";

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.redirect(new URL("/?error=session", getFallbackUrl()));
  try {
    const config = getConfig();
    const transaction = await startAdminConsentTransaction(session.tenantId);
    const consentUrl = new URL(
      `https://login.microsoftonline.com/${session.tenantId}/v2.0/adminconsent`,
    );
    consentUrl.search = new URLSearchParams({
      client_id: config.ENTRA_CLIENT_ID,
      scope: "https://graph.microsoft.com/.default",
      redirect_uri: `${config.APP_URL}/api/onboarding/callback/microsoft`,
      state: transaction.state,
    }).toString();
    return NextResponse.redirect(consentUrl);
  } catch {
    return NextResponse.redirect(new URL("/runs/latest?onboarding=configuration", getFallbackUrl()));
  }
}

function getFallbackUrl(): string {
  return process.env.APP_URL || "http://localhost:3000";
}
