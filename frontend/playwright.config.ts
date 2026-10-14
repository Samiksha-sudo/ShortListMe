import { defineConfig } from "@playwright/test";

// Expects the API on :8000 and the Vite dev server on :5173 (see ../start.sh).
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:5173", trace: "retain-on-failure" },
  webServer: [
    { command: "npm run dev", url: "http://localhost:5173", reuseExistingServer: true },
  ],
});
