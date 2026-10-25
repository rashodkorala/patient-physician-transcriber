import type { NextConfig } from "next";

// The TV loads /screen from the laptop's address on the local network. In development Next.js
// only trusts localhost for its hot-reload socket, so allow private networks and Mac `.local`
// names too; a refused socket shows an error badge on the TV. No effect on `next start`.
const PRIVATE_NETWORKS = [
  "192.168.*.*",
  "10.*.*.*",
  ...Array.from({ length: 16 }, (_, i) => `172.${16 + i}.*.*`),
  "*.local",
];

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  allowedDevOrigins: PRIVATE_NETWORKS,
  // Keep the Next.js badge off the TV during dev runs; error overlays still appear.
  devIndicators: false,
};

export default nextConfig;
