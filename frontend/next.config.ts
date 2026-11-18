import type { NextConfig } from "next";

// HTTP data source: the browser talks to Laravel through this origin (same-origin cookies, no CORS).
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const proxyApi = process.env.NEXT_PUBLIC_DATA_SOURCE === "http";

const nextConfig: NextConfig = {
  // Standalone output keeps the Docker runtime image small.
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  async redirects() {
    return [
      { source: "/", destination: "/login", permanent: false },
      { source: "/analysis", destination: "/analysis/RELIANCE", permanent: false },
    ];
  },
  async rewrites() {
    return proxyApi
      ? [
          { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
          { source: "/sanctum/:path*", destination: `${BACKEND_URL}/sanctum/:path*` },
        ]
      : [];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
