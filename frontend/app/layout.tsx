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
  title: "PolicyEngine poverty dashboard",
  description:
    "Internal dashboard tracking baseline federal and per-state poverty and child poverty rates from PolicyEngine-US.",
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
