import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Curio AI - Learn by Teaching",
  description: "A Feynman Technique inspired learning platform where the AI acts as your curious student.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
