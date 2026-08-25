import { Verdict } from "@/lib/types";
export function Status({ verdict }: { verdict: Verdict }) { return <span className={`status ${verdict.toLowerCase()}`}>{verdict.replace("_", " ")}</span>; }
