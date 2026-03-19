/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'api.dicebear.com',
      },
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
      },
    ],
  },
  async rewrites() {
    return [
        {
          source: '/api/auth/:path*',
          destination: '/api/auth/:path*',
        },
      {
        // Proxy all API routes to Flask backend EXCEPT auth routes
        // Auth routes are handled by Better Auth in Next.js
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ]
  },
  webpack: (config) => {
    config.externals.push("better-sqlite3");
    return config;
  },
}

module.exports = nextConfig
