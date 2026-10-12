import type { NextConfig } from "next";

const basePath = process.env.BASE_PATH || "";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: process.env.STATIC_EXPORT === "1" ? "export" : undefined,
  trailingSlash: process.env.STATIC_EXPORT === "1",
  basePath,
  assetPrefix: basePath || undefined,
};

export default nextConfig;
