import { redirect } from "next/navigation";
import { getSession } from "@/lib/auth";

export async function requireSession() {
  const session = await getSession();
  if (!session) redirect("/");
  return session;
}
