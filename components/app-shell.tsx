import Link from "next/link";

export function AppShell({ children }: { children: React.ReactNode }) {
  return <main className="shell"><nav className="nav"><Link className="brand" href="/"><span>nis2</span>check</Link><div className="navlinks"><Link href="/runs/latest">Latest run</Link><Link href="/compare">Compare runs</Link><a href="https://github.com/TheDarthAdmin/nis2check">Open source</a></div></nav>{children}</main>;
}
