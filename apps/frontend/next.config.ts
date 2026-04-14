import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'http://localhost:8000/:path*',
      },
      {
        source: '/api/crawler/:path*',
        destination: 'http://localhost:8001/:path*',
      },
    ]
  },
}

export default nextConfig
