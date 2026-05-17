import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Header, PageHeader } from "@/components/Header";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "PolicyEngine 2024 SPM comparison",
  description:
    "Internal dashboard comparing PolicyEngine-US 2024 SPM-like results with Census SPM report benchmarks.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen">
        <Providers>
          <Header />
          <PageHeader />
          {children}
        </Providers>
      </body>
    </html>
  );
}
