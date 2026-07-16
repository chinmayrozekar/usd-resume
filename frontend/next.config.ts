import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next spawns build workers based on the host's detected CPU count, which
  // on Vercel's build container reflects the physical host, not the
  // container's actual cgroup-limited cores/memory -- so it over-forks and
  // gets SIGKILLed. Forcing a single worker trades build speed for staying
  // under the real memory ceiling.
  experimental: {
    cpus: 1,
    workerThreads: false,
    // Reduces webpack's peak heap during compilation (string interning /
    // dual buffer caching) at a small cost to build time -- see
    // https://nextjs.org/docs/app/guides/memory-usage
    webpackMemoryOptimizations: true,
  },
  webpack: (config, { dev }) => {
    // The webpack cache (filesystem or in-memory) exists to speed up
    // *repeat* builds, but each Vercel deploy is a fresh container with
    // nothing to reuse -- it only adds peak memory for zero benefit here.
    if (!dev) {
      config.cache = false;
    }
    return config;
  },
};

export default nextConfig;
