import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Customer Support | Digital FTE",
  description:
    "24/7 AI-powered customer success platform. Get instant answers, smart routing, and human escalation when needed.",
  keywords: ["AI support", "customer success", "digital FTE", "chatbot"],
  authors: [{ name: "Digital FTE Team" }],
  openGraph: {
    title: "AI Customer Support | Digital FTE",
    description: "24/7 AI-powered customer success platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <meta name="theme-color" content="#0f0c29" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
