import { Verdict } from "@/lib/demo";
export function Status({ verdict }: { verdict: Verdict }) { return <span className={`status ${verdict.toLowerCase()}`}>{verdict.replace("_", " ")}</span>; }
