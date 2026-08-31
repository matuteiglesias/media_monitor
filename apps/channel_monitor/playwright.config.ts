import { defineConfig } from "@playwright/test";
export default defineConfig({ testDir: "./tests", timeout: 30_000, use: { baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3010", screenshot: "only-on-failure", trace: "retain-on-failure" } });
