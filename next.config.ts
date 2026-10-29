import type { NextConfig } from 'next';
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "standalone",
  trailingSlash: true,
  images: { unoptimized: true },
};
export default nextConfig;
