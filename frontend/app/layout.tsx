import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LARISKA AI — Sales Brain UMKM",
  description: "Platform Sales Intelligence untuk UMKM Indonesia.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="id"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
