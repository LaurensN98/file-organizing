import Image from "next/image";
import Link from "next/link";

export default function Navbar() {
  const links = [
    // { name: "History", href: "/history" },
    { name: "Organize", href: "/" },
    { name: "Pricing", href: "/#pricing" },
    { name: "About", href: "/#about" },
    { name: "Contact", href: "/#contact" },
  ];

  return (
    <div className="w-full h-20 sticky top-0 left-0 z-50 bg-white shadow-md flex items-center px-6 text-black">
      <Link href="/" className="absolute">
        <div className="w-32 select-none">
          <Image
            src="/svgs/logo.svg"
            alt="Logo"
            width={1469}
            height={414}
            style={{
              width: "100%",
              height: "auto",
            }}
            priority
          />
        </div>
      </Link>

      <div className="flex items-center gap-16 w-full justify-center">
        {links.map((link) => (
          <Link key={link.name} href={link.href}>
            <div className="font-semibold text-[#203047] hover:text-[#4A80A6]">
              {link.name}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
