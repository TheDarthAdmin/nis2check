import Link from "next/link";
import { getSession } from "@/lib/auth";

export async function AppShell({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  return <main className="shell"><nav className="nav"><Link className="brand" href="/"><span>nis2</span>check</Link><div className="navlinks"><Link href="/runs/latest">Latest run</Link><Link href="/compare">Compare runs</Link><a href="https://github.com/TheDarthAdmin/nis2check">Open source</a>{session ? <form action="/api/auth/signout" method="post"><button className="nav-button" type="submit">Sign out</button></form> : <a className="nav-button" href="/api/auth/signin">Sign in</a>}</div></nav>{children}</main>;
}
