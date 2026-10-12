import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NeoMint - Learn markets by playing them",
  description: "Gamified financial literacy and simulated trading sandbox",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
