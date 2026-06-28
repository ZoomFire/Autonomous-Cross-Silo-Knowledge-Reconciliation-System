import { describe, expect, test, vi } from "vitest";

describe("API base URL configuration", () => {
  test("uses VITE_API_BASE_URL when provided", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://backend.example.com");
    vi.resetModules();

    const { API_BASE_URL } = await import("../api.js");

    expect(API_BASE_URL).toBe("https://backend.example.com");
  });

  test("falls back to the local backend URL", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    vi.resetModules();

    const { API_BASE_URL } = await import("../api.js");

    expect(API_BASE_URL).toBe("http://localhost:8000");
  });
});
