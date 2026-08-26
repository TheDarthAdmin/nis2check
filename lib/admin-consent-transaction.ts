import { randomBytes } from "crypto";
import { cookies } from "next/headers";

const transactionCookie = "nis2check_admin_consent";

export type AdminConsentTransaction = {
  state: string;
  tenantId: string;
};

function cookieOptions(maxAge?: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    ...(maxAge === undefined ? {} : { maxAge }),
  };
}

export async function startAdminConsentTransaction(tenantId: string): Promise<AdminConsentTransaction> {
  const transaction = { state: randomBytes(32).toString("base64url"), tenantId };
  (await cookies()).set(transactionCookie, JSON.stringify(transaction), cookieOptions(10 * 60));
  return transaction;
}

export async function consumeAdminConsentTransaction(): Promise<AdminConsentTransaction | null> {
  const store = await cookies();
  const value = store.get(transactionCookie)?.value;
  store.set(transactionCookie, "", cookieOptions(0));
  if (!value) return null;
  try {
    const transaction = JSON.parse(value) as AdminConsentTransaction;
    if (!transaction.state || !transaction.tenantId) return null;
    return transaction;
  } catch {
    return null;
  }
}
