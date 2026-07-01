import { afterEach, describe, expect, test, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

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

    expect(API_BASE_URL).toBe("http://127.0.0.1:8001");
  });

  test("does not attach authorization headers to feature API calls", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://backend.example.com");
    vi.resetModules();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "ok" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getHealth } = await import("../api.js");
    await getHealth();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty("Authorization");
  });
});
