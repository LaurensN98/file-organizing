import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

const footerLinks = [
  {
    title: "Product",
    links: [
      { name: "Features", href: "/#features" },
      { name: "History", href: "/history" },
      { name: "Pricing", href: "/#pricing" },
      { name: "Support", href: "mailto:support@neatly.com" },
    ],
  },
  {
    title: "Company",
    links: [
      { name: "About Us", href: "/#about" },
      { name: "Blog", href: "/#blog" },
      { name: "Careers", href: "/#careers" },
      { name: "Contact", href: "/#contact" },
    ],
  },
  {
    title: "Legal",
    links: [
      { name: "Privacy Policy", href: "/privacy" },
      { name: "Terms of Service", href: "/terms" },
      { name: "Cookie Policy", href: "/cookies" },
    ],
  },
];

const socialLinks = [
  {
    icon: <i className="bi bi-twitter-x"></i>,
    href: "https://twitter.com",
    label: "Twitter",
  },
  {
    icon: <i className="bi bi-linkedin"></i>,
    href: "https://linkedin.com",
    label: "LinkedIn",
  },
  {
    icon: <i className="bi bi-github"></i>,
    href: "https://github.com",
    label: "GitHub",
  },
  {
    icon: <i className="bi bi-envelope-fill"></i>,
    href: "mailto:hello@neatly.com",
    label: "Email",
  },
];

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <div className="bg-white">
      <footer className="w-full bg-white border-t border-gray-100 py-20 px-12 overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 lg:gap-8 mb-16">
            {/* Brand Column */}
            <div className="lg:col-span-2 space-y-6">
              <Link href="/" className="inline-block group">
                <div className="w-48">
                  <Image
                    src="/svgs/logo.svg"
                    alt="Neatly Logo"
                    width={1469}
                    height={394}
                    style={{ width: "100%", height: "auto" }}
                  />
                </div>
              </Link>
              <p className="text-gray-500 max-w-sm text-sm leading-relaxed">
                Neatly helps you organize your files with ease. Our solution
                ensures your documents are always where they belong.
              </p>
              <div className="flex gap-4">
                {socialLinks.map((social) => (
                  <Link
                    key={social.label}
                    href={social.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#203047] hover:text-black duration-300"
                    aria-label={social.label}
                  >
                    {social.icon}
                  </Link>
                ))}
              </div>
            </div>

            {/* Links Columns */}
            {footerLinks.map((section) => (
              <div key={section.title} className="space-y-6">
                <h4 className="text-sm font-bold text-[#203047] uppercase tracking-wider">
                  {section.title}
                </h4>
                <ul className="space-y-4">
                  {section.links.map((link) => (
                    <li key={link.name}>
                      <Link
                        href={link.href}
                        className="text-gray-500 hover:text-[#203047] text-sm transition-colors duration-200 flex items-center group"
                      >
                        {link.name}
                        <ArrowUpRight
                          size={12}
                          className="ml-1 opacity-0 -translate-y-1 translate-x-1 group-hover:opacity-100 group-hover:translate-y-0 group-hover:translate-x-0 transition-all duration-200"
                        />
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Bottom Bar */}
          <div className="pt-8 border-t border-gray-100 flex flex-col md:flex-row justify-between items-center gap-4">
            <p className="text-gray-400 text-sm">
              © {currentYear} Neatly. All rights reserved.
            </p>
            <div className="flex items-center gap-6">
              <Link
                href="/privacy"
                className="text-gray-400 hover:text-[#203047] text-sm transition-colors"
              >
                Privacy Policy
              </Link>
              <Link
                href="/terms"
                className="text-gray-400 hover:text-[#203047] text-sm transition-colors"
              >
                Terms of Service
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
