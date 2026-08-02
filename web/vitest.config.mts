import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: [
      {
        find: "server-only",
        replacement: fileURLToPath(new URL("./test/server-only.ts", import.meta.url)),
      },
      {
        find: "@",
        replacement: fileURLToPath(new URL("./src", import.meta.url)),
      },
    ],
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
    restoreMocks: true,
  },
});
