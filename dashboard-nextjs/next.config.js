/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/status",
        destination: "http://localhost:8080/api/status",
      },
    ];
  },
};
module.exports = nextConfig;
