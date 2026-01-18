/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow images from external domains
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'cdn.discord.com' },
      { protocol: 'https', hostname: 'avatars.slack-edge.com' },
      { protocol: 'https', hostname: 'lh3.googleusercontent.com' },
    ],
  },

  // Redirects (e.g., old routes to new)
  async redirects() {
    return [
      { source: '/lobby', destination: '/sessions', permanent: true },
    ];
  },

  // Environment variable validation
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_ENVIRONMENT: process.env.NEXT_PUBLIC_ENVIRONMENT,
  },
};

module.exports = nextConfig;
