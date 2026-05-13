/** @type {import('next').NextConfig} */
const mediaBase = process.env.NEXT_PUBLIC_MEDIA_BASE_URL;

const mediaRemotePatterns = [];
if (mediaBase) {
  try {
    const mediaUrl = new URL(mediaBase);
    mediaRemotePatterns.push({
      protocol: mediaUrl.protocol.replace(":", ""),
      hostname: mediaUrl.hostname,
      port: mediaUrl.port || "",
      pathname: "/**",
    });
  } catch {
    // Ignore malformed URL at build time; app will continue with local fallbacks.
  }
}

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
      ...mediaRemotePatterns,
    ],
  },
  webpack(config) {
    config.module.rules.push({
      test: /\.(mp4|webm)$/,
      type: "asset/resource",
      generator: {
        filename: "static/media/[name].[hash][ext]",
      },
    });

    return config;
  },
};

module.exports = nextConfig;
