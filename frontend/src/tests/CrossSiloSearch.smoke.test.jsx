import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CrossSiloSearch from "../pages/CrossSiloSearch.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  buildRagIndex: vi.fn(),
  exportRagSearchMarkdown: vi.fn(),
  getImportedSources: vi.fn(() => Promise.resolve([])),
  getRagChunks: vi.fn(() => Promise.resolve([])),
  getRagSearchHistory: vi.fn(() => Promise.resolve([])),
  getRagSearchHistoryItem: vi.fn(),
  ragSearch: vi.fn(),
  runHybridReasoning: vi.fn(),
}));

describe("CrossSiloSearch smoke", () => {
  it("renders search input and button", () => {
    render(<CrossSiloSearch user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByLabelText("Ask a question")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  });
});
