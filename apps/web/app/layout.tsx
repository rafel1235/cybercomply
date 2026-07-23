import type { Metadata } from "next";
import { Providers } from "@/components/providers/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "CyberComplyIT — Conformità NIS2 e CRA per PMI italiane",
  description:
    "Piattaforma italiana di cyber-compliance: NIS2, Cyber Resilience Act e D.Lgs. 138/2024 per le PMI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
