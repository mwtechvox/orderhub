import type { NextConfig } from "next";

const backendOrigin = (
  process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*/`,
      },
      {
        source: "/health/:path*",
        destination: `${backendOrigin}/health/:path*/`,
      },
    ];
  },
};
export default config;
