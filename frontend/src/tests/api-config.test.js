import { afterEach, describe, expect, test, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("API base URL configuration", () => {
  test("uses VITE_API_BASE_URL when provided", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://backend.example.com/");
    vi.resetModules();

    const { API_BASE_URL } = await import("../api.js");

    expect(API_BASE_URL).toBe("https://backend.example.com");
  });

  test("falls back to a local backend in development when VITE_API_BASE_URL is not provided", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    vi.resetModules();

    const { API_BASE_URL } = await import("../api.js");

    expect(API_BASE_URL).toBe("http://localhost:8000");
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

  test("health check calls the backend /health endpoint", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://backend.example.com");
    vi.resetModules();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "ok", storage_available: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getHealth } = await import("../api.js");
    await expect(getHealth()).resolves.toMatchObject({ status: "ok" });

    expect(fetchMock.mock.calls[0][0]).toBe("https://backend.example.com/health");
  });

  test("health check rejects unexpected backend health status", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://backend.example.com");
    vi.resetModules();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "healthy" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getHealth } = await import("../api.js");

    await expect(getHealth()).rejects.toThrow("Backend health check failed");
  });

  test("logs the final API URL when a request cannot reach the backend", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://backend.example.com");
    vi.resetModules();
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal("fetch", fetchMock);

    const { getHealth } = await import("../api.js");

    await expect(getHealth()).rejects.toThrow("Backend unavailable");
    expect(errorSpy).toHaveBeenCalledWith(
      "[DriftGuard API] Backend request failed",
      expect.objectContaining({ url: "https://backend.example.com/health" }),
    );
  });
});
