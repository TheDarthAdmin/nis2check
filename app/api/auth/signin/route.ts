import { NextResponse } from "next/server";
import { codeChallenge, startAuthTransaction } from "@/lib/auth-transaction";
import { getConfig } from "@/lib/env";

export const runtime = "nodejs";

export async function GET() {
  try {
    const config = getConfig();
    const transaction = await startAuthTransaction();
    const authorizeUrl = new URL(
      "https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize",
    );
    authorizeUrl.search = new URLSearchParams({
      client_id: config.ENTRA_CLIENT_ID,
      response_type: "code",
      redirect_uri: `${config.APP_URL}/api/auth/callback/microsoft`,
      response_mode: "query",
      scope: "openid profile email",
      state: transaction.state,
      nonce: transaction.nonce,
      code_challenge: codeChallenge(transaction.codeVerifier),
      code_challenge_method: "S256",
    }).toString();
    return NextResponse.redirect(authorizeUrl);
  } catch {
    return NextResponse.redirect(new URL("/?error=configuration", getFallbackUrl()));
  }
}

function getFallbackUrl(): string {
  return process.env.APP_URL || "http://localhost:3000";
}
