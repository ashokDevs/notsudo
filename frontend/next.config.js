/** @type {import('next').NextConfig} */
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
        destination: 'http://localhost:8000/api/:path*',
        has: [
          {
            type: 'header',
            key: 'x-skip-auth-check',
            value: undefined,
          },
        ],
      },
      {
        // Fallback: proxy non-auth API routes
        source: '/api/((?!auth).*)',
        destination: 'http://localhost:8000/api/$1',
      },
    ]
  },
  webpack: (config) => {
    config.externals.push("better-sqlite3");
    return config;
  },
}

module.exports = nextConfig
