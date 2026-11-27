import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NyayaSathi — Know your rights. Find your next step.",
  description: "Understand everyday legal issues in India with plain-English guidance, official sources and routes to free legal aid.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
