const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname, '..'),
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: '/ws/:path*',
        destination: 'http://localhost:8003/ws/:path*',
      },
      {
        source: '/api/stats/:path*',
        destination: 'http://localhost:8003/api/stats/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
