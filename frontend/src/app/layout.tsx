import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Customer Support - Digital FTE",
  description: "24/7 AI Customer Success Support",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
