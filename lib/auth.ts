import { createRemoteJWKSet, jwtVerify, SignJWT } from "jose";
import { cookies } from "next/headers";
import { getConfig, isConfigured } from "@/lib/env";

const sessionCookie = "nis2check_session";
const encoder = new TextEncoder();

export type Session = {
  name: string;
  username: string;
  subject: string;
  tenantId: string;
};

type IdTokenClaims = {
  name?: string;
  preferred_username?: string;
  sub?: string;
  tid?: string;
  nonce?: string;
  iss?: string;
};

function sessionKey() {
  return encoder.encode(getConfig().AUTH_SECRET);
}

function cookieOptions(maxAge?: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    ...(maxAge === undefined ? {} : { maxAge }),
  };
}

export async function getSession(): Promise<Session | null> {
  if (!isConfigured()) return null;
  const token = (await cookies()).get(sessionCookie)?.value;
  if (!token) return null;

  try {
    const { payload } = await jwtVerify(token, sessionKey(), { algorithms: ["HS256"] });
    if (
      typeof payload.name !== "string" ||
      typeof payload.username !== "string" ||
      typeof payload.subject !== "string" ||
      typeof payload.tenantId !== "string"
    ) {
      return null;
    }
    return {
      name: payload.name,
      username: payload.username,
      subject: payload.subject,
      tenantId: payload.tenantId,
    };
  } catch {
    return null;
  }
}

export async function setSession(session: Session): Promise<void> {
  const token = await new SignJWT(session)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("8h")
    .sign(sessionKey());
  (await cookies()).set(sessionCookie, token, cookieOptions(60 * 60 * 8));
}

export async function clearSession(): Promise<void> {
  (await cookies()).set(sessionCookie, "", cookieOptions(0));
}

export async function verifyMicrosoftIdToken(idToken: string, expectedNonce: string): Promise<Session> {
  const config = getConfig();
  const jwks = createRemoteJWKSet(
    new URL("https://login.microsoftonline.com/organizations/discovery/v2.0/keys"),
  );
  const { payload } = await jwtVerify<IdTokenClaims>(idToken, jwks, {
    algorithms: ["RS256"],
    audience: config.ENTRA_CLIENT_ID,
  });

  if (
    payload.nonce !== expectedNonce ||
    !payload.sub ||
    !isTenantId(payload.tid) ||
    payload.iss !== `https://login.microsoftonline.com/${payload.tid}/v2.0`
  ) {
    throw new Error("Microsoft returned an invalid identity token.");
  }

  return {
    name: payload.name || payload.preferred_username || "Microsoft user",
    username: payload.preferred_username || "Signed-in Microsoft user",
    subject: payload.sub,
    tenantId: payload.tid,
  };
}

function isTenantId(value: string | undefined): value is string {
  return Boolean(value && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value));
}
