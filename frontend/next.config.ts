import type { NextConfig } from "next";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  basePath,
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
    NEXT_PUBLIC_MODAL_BASE_URL: process.env.NEXT_PUBLIC_MODAL_BASE_URL || "",
  },
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
