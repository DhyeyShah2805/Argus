import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Argus — Equity Research",
  description: "Multi-agent equity research. Six agents, one query.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
