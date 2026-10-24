import type { Metadata } from "next";
import "@fontsource/noto-sans-gurmukhi/400.css";
import "@fontsource/noto-sans-gurmukhi/600.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Demo Night Interpreter",
  description: "Live medical interpretation between a patient and a physician.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
