/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  distDir: process.env.AEGIS_NEXT_DIST_DIR || ".next-live",
};

module.exports = nextConfig;
