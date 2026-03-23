import type { Metadata } from "next";
import localFont from "next/font/local";
import "../globals.css";
import Image from "next/image";
import Link from "next/link";
import Footer from "@/components/Footer";

const satoshi = localFont({
  src: "../../../public/fonts/Satoshi-Variable.ttf", // Path to your font file
  variable: "--font-satoshi", // Optional: defines a CSS variable
});

const manrope = localFont({
  src: "../../../public/fonts/Manrope-VariableFont_wght.ttf",
  variable: "--font-manrope",
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
      <body
        className={`${satoshi.className} ${manrope.variable} text-[#203047] bg-white`}
      >
        <nav className="flex sticky top-0 z-50 items-center justify-between py-6 px-8 mx-auto w-full border-b border-gray-100 bg-white/80 backdrop-blur-md">
          <div className="flex items-center">
            <Link href="/">
              <Image
                src="/svgs/logo.svg"
                alt="Neatly Logo"
                width={120}
                height={40}
                className="object-contain w-32"
              />
            </Link>
          </div>
          <div className="hidden md:flex items-center gap-16 text-gray-500 font-medium">
            <Link
              href="#features"
              className="hover:text-gray-900 transition-colors"
            >
              Features
            </Link>
            <Link
              href="#pricing"
              className="hover:text-gray-900 transition-colors"
            >
              Pricing
            </Link>
            <Link
              href="#about"
              className="hover:text-gray-900 transition-colors"
            >
              About
            </Link>
          </div>
          <div className="flex items-center gap-8 font-medium">
            <Link
              href="/login"
              className="text-gray-900 hover:text-gray-700 transition-colors hidden sm:block"
            >
              Log In
            </Link>
            <Link
              href="/signup"
              className="bg-gradient-primary hover:opacity-90 text-white px-6 py-2.5 rounded-full transition-all text-sm shadow-sm"
            >
              Sign Up Free
            </Link>
          </div>
        </nav>
        {children}
        <Footer />
      </body>
    </html>
  );
}
