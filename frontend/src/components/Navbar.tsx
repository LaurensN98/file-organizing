import Image from "next/image";
import Link from "next/link";

export default function Navbar() {
  return (
    <div className="w-full h-20 sticky top-0 left-0 z-50 bg-white shadow-md flex justify-between items-center px-6 text-black">
      <Link href="/">
        <div className="w-32">
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

      <Link href="/history">
        <div className="font-semibold text-[#203047] hover:text-blue-500">
          History
        </div>
      </Link>
    </div>
  );
}
