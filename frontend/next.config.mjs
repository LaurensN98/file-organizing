/** @type {import('next').NextConfig} */
const nextConfig = {
  // Transpiling libraries can help resolve source map issues by processing them with Next.js's toolchain
  transpilePackages: ["framer-motion"],

  webpack: (config, { dev }) => {
    // Suppress console warnings about missing source maps in development
    if (dev) {
      config.ignoreWarnings = [
        { module: /node_modules\/framer-motion/ },
        { message: /Failed to parse source map/ },
      ];
    }
    return config;
  },
};

export default nextConfig;
