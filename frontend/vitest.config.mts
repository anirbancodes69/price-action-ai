import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    // Formatting is pinned to en-IN / Asia/Kolkata; keep the runner's TZ neutral.
    env: { TZ: "UTC" },
  },
});
