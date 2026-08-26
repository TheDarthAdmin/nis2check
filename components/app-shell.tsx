import Link from "next/link";
import { getSession } from "@/lib/auth";

export async function AppShell({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  return <main className="shell"><nav className="nav"><Link className="brand" href="/"><span className="brand-mark">N</span><span>nis2</span>check</Link><div className="navlinks"><Link href="/runs/latest">Evidence</Link><Link href="/compare">Compare</Link><a href="https://github.com/TheDarthAdmin/nis2check">Documentation</a>{session ? <><span className="user-chip" title={session.username}>{session.name}</span><form action="/api/auth/signout" method="post"><button className="nav-button quiet-button" type="submit">Sign out</button></form></> : <a className="nav-button" href="/api/auth/signin">Sign in</a>}</div></nav>{children}</main>;
}
