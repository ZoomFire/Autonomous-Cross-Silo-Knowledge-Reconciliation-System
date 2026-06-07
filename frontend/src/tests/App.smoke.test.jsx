import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "../App.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  clearAuthToken: vi.fn(),
  getAuthToken: () => "",
  getCurrentUser: vi.fn(),
  getSelectedWorkspaceId: () => "",
  getWorkspaces: vi.fn(),
  logout: vi.fn(),
  setSelectedWorkspaceId: vi.fn(),
  login: vi.fn(),
}));

describe("App smoke", () => {
  it("renders without crashing", () => {
    render(<App />);
    expect(screen.getByText("DriftGuard AI")).toBeInTheDocument();
  });
});
