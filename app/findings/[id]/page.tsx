import { redirect } from "next/navigation";
import { requireSession } from "@/lib/require-session";

export default async function LegacyFinding() {
  await requireSession();
  redirect("/runs/latest");
}
