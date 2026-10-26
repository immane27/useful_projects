import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "File Processing Check",
  description: "Sanity check for TAP file processing configuration",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
