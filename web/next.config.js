const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname, '..'),
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const apiBase = process.env.API_BASE_URL || 'http://localhost:8003';
    return [
      {
        source: '/ws/:path*',
        destination: `${apiBase}/ws/:path*`,
      },
      {
        source: '/api/stats/:path*',
        destination: `${apiBase}/api/stats/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
