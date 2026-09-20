import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Jev Decision Lab",
    template: "%s · Jev Decision Lab",
  },
  applicationName: "Jev Decision Lab",
  description: "A live benchmark showing where deterministic rules stop and Jev decisions become useful.",
  authors: [{ name: "Rad Rebel Developer", url: "https://radrebeldeveloper.com" }],
  creator: "Rad Rebel Developer",
  openGraph: {
    title: "Jev Decision Lab",
    description: "Rules for the obvious. Jev for the ambiguous.",
    type: "website",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>{children}</body>
    </html>
  );
}
