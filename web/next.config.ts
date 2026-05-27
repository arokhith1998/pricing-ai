import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The blog routes read content/blog/*.md at request time; make sure those
  // files are traced into the serverless bundle on Vercel.
  outputFileTracingIncludes: {
    "/blog": ["./content/blog/**/*"],
    "/blog/[slug]": ["./content/blog/**/*"],
  },
};

export default nextConfig;
