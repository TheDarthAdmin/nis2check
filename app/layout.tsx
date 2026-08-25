import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nis2Check | Technical evidence, not a score",
  description: "Read-only Microsoft 365 evidence collection for technically verifiable NIS2 controls.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
