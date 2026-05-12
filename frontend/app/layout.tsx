import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "PolicyEngine Poverty Dashboard",
  description:
    "Internal dashboard tracking baseline federal and per-state poverty and child poverty rates from PolicyEngine-US.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
