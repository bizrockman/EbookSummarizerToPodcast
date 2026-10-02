import type { Metadata } from "next";
import "./globals.css";


export const metadata: Metadata = {
  title: "Ebook Audio Studio",
  description: "Bücher sinnvoll kürzen, in passender Tiefe lesen und unterwegs hören."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body className="font-sans">{children}</body>
    </html>
  );
}
