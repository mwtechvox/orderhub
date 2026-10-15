import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  use: { baseURL: "http://localhost:3000", channel: "chrome" },
  webServer: {
    command: "npm run start",
    url: "http://localhost:3000/login",
    reuseExistingServer: true,
    timeout: 60000,
  },
});
