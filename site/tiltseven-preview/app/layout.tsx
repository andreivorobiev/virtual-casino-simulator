import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TiltSeven",
  description:
    "TiltSeven is a private play-token casino simulator with casino-floor energy and no cash value.",
  icons: {
    icon: "/tiltseven-mark.svg",
    shortcut: "/tiltseven-mark.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
