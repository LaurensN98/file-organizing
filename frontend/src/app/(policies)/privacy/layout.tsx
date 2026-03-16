import localFont from "next/font/local";
import "../../globals.css";

// Configure Satoshi
const satoshi = localFont({
  src: "../../../../public/fonts/Satoshi-Variable.ttf", // Path to your font file
  variable: "--font-satoshi", // Optional: defines a CSS variable
});

export default function PrivacyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${satoshi.className} text-[#203047]`}>{children}</body>
    </html>
  );
}
