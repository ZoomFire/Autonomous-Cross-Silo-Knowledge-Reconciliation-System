import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "../App.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  getSelectedWorkspaceId: () => "",
  getWorkspaces: vi.fn(),
  setSelectedWorkspaceId: vi.fn(),
}));

describe("App smoke", () => {
  it("renders without crashing", () => {
    render(<App />);
    expect(screen.getByText("DriftGuard AI")).toBeInTheDocument();
  });
});
