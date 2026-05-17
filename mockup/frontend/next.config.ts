import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    // SVGs corporativos (logos UPV/ETSINF) servidos desde /public.
    // Confiamos en el contenido porque lo subimos nosotros mismos.
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  async rewrites() {
    const backendBase = process.env.API_BASE_URL_INTERNAL || "http://127.0.0.1:8000/api/v1";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendBase}/:path*`,
      },
    ];
  },
};

export default nextConfig;
