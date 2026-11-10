import type { Metadata, Viewport } from "next";
// ADR-012: one legibility-first family for Latin script, and Noto Sans for the three other scripts in use.
import "@fontsource-variable/atkinson-hyperlegible-next";
import "@fontsource/noto-sans-gurmukhi/400.css";
import "@fontsource/noto-sans-gurmukhi/500.css";
import "@fontsource/noto-sans-gurmukhi/600.css";
import "@fontsource/noto-sans-sinhala/400.css";
import "@fontsource/noto-sans-sinhala/500.css";
import "@fontsource/noto-sans-sinhala/600.css";
import "@fontsource/noto-sans-tamil/400.css";
import "@fontsource/noto-sans-tamil/500.css";
import "@fontsource/noto-sans-tamil/600.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Medical interpreter",
  description: "Live medical interpretation between a patient and a physician, with a record both can trust.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f7f6" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1a1d" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
