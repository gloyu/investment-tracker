import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Investing Recap Dashboard",
  description: "Factual, RAG-grounded market recaps for your watchlist.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0 }}>
        <nav
          style={{
            display: "flex",
            gap: "1.5rem",
            padding: "1rem 1.5rem",
            borderBottom: "1px solid #e5e5e5",
          }}
        >
          <Link href="/">Latest Report</Link>
          <Link href="/watchlist">Watchlist</Link>
          <Link href="/runs">Run Status</Link>
        </nav>
        <main style={{ padding: "1.5rem" }}>{children}</main>
      </body>
    </html>
  );
}
