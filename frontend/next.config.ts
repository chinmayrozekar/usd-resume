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
  },
};

export default nextConfig;
