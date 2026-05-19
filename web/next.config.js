const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname, '..'),
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const apiBase = process.env.API_BASE_URL || 'http://localhost:8001';
    return [
      {
        source: '/api/:path*',
        destination: `${apiBase}/api/:path*`,
      },
      {
        source: '/ws/:path*',
        destination: `${apiBase}/ws/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
