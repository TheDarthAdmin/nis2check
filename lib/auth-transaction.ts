import { randomBytes, createHash } from "crypto";
import { cookies } from "next/headers";

const transactionCookie = "nis2check_auth_transaction";

export type AuthTransaction = {
  state: string;
  nonce: string;
  codeVerifier: string;
};

function randomValue(): string {
  return randomBytes(32).toString("base64url");
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

export function codeChallenge(verifier: string): string {
  return createHash("sha256").update(verifier).digest("base64url");
}

export async function startAuthTransaction(): Promise<AuthTransaction> {
  const transaction = { state: randomValue(), nonce: randomValue(), codeVerifier: randomValue() };
  (await cookies()).set(transactionCookie, JSON.stringify(transaction), cookieOptions(10 * 60));
  return transaction;
}

export async function consumeAuthTransaction(): Promise<AuthTransaction | null> {
  const store = await cookies();
  const value = store.get(transactionCookie)?.value;
  store.set(transactionCookie, "", cookieOptions(0));
  if (!value) return null;

  try {
    const transaction = JSON.parse(value) as AuthTransaction;
    if (!transaction.state || !transaction.nonce || !transaction.codeVerifier) return null;
    return transaction;
  } catch {
    return null;
  }
}
