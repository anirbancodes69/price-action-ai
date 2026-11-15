import type { NextConfig } from "next";

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
