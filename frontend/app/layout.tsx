import type { Metadata } from "next";
import { Sora, DM_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { CurioToaster } from "@/components/curio/CurioToast";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Curio AI - Learn by Teaching (Feynman Technique)",
  description: "Explain what you know. Curio challenges your thinking, uncovers your knowledge gaps, and helps you truly understand.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${sora.variable} ${dmSans.variable} ${ibmPlexMono.variable}`}
    >
      <body className="antialiased min-h-screen bg-ice text-navy font-sans selection:bg-cobalt selection:text-white">
        {children}
        <CurioToaster />
      </body>
    </html>
  );
}

