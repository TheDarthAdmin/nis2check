"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Keeps a running collection on screen up to date without the reader pressing reload. */
export function AutoRefresh({ intervalMs = 10_000 }: { intervalMs?: number }) {
  const router = useRouter();
  useEffect(() => {
    const timer = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(timer);
  }, [router, intervalMs]);
  return null;
}
