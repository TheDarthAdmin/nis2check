import { NextRequest, NextResponse } from "next/server";
import { consumeAuthTransaction } from "@/lib/auth-transaction";
import { setSession, verifyMicrosoftIdToken } from "@/lib/auth";
import { getConfig } from "@/lib/env";

export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const failure = (reason: string) =>
    NextResponse.redirect(new URL(`/?error=${encodeURIComponent(reason)}`, getFallbackUrl()));
  const microsoftError = request.nextUrl.searchParams.get("error");
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const transaction = await consumeAuthTransaction();

  if (microsoftError || !code || !state || !transaction || state !== transaction.state) {
    return failure(microsoftError ? "microsoft" : "state");
  }

  try {
    const config = getConfig();
    const response = await fetch(
      "https://login.microsoftonline.com/organizations/oauth2/v2.0/token",
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        cache: "no-store",
        body: new URLSearchParams({
          client_id: config.ENTRA_CLIENT_ID,
          client_secret: config.ENTRA_CLIENT_SECRET,
          grant_type: "authorization_code",
          code,
          redirect_uri: `${config.APP_URL}/api/auth/callback/microsoft`,
          code_verifier: transaction.codeVerifier,
          scope: "openid profile email",
        }),
      },
    );
    const tokens = (await response.json()) as { id_token?: string };
    if (!response.ok || !tokens.id_token) return failure("token");

    await setSession(await verifyMicrosoftIdToken(tokens.id_token, transaction.nonce));
    return NextResponse.redirect(new URL("/runs/latest", config.APP_URL));
  } catch {
    return failure("token");
  }
}

function getFallbackUrl(): string {
  return process.env.APP_URL || "http://localhost:3000";
}
