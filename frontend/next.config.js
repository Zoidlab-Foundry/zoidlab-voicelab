/** @type {import('next').NextConfig} */
// VoiceLab's own FastAPI backend. Must point at THIS app's API, not a sibling's.
const API = process.env.VOICELAB_API_URL || "http://127.0.0.1:8705";
module.exports = {
  reactStrictMode: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};
