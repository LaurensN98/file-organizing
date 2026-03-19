import type { Metadata } from "next";
import localFont from "next/font/local";
import "../globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const satoshi = localFont({
  src: "../../../public/fonts/Satoshi-Variable.ttf", // Path to your font file
  variable: "--font-satoshi", // Optional: defines a CSS variable
});

export const metadata: Metadata = {
  title: "Organize Your File Automatically | Neatly",
  description: "Organize your messy files into structured folders with AI.",
  manifest: "/site.webmanifest",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${satoshi.className} text-[#203047]`}>
        <Navbar />
        {children}
        <Footer />
      </body>
    </html>
  );
}
