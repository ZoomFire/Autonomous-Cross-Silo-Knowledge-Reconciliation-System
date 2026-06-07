import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AgentDashboard from "../pages/AgentDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  createAgentPlan: vi.fn(),
  deleteAgentRun: vi.fn(),
  exportAgentReportJson: vi.fn(),
  exportAgentReportMarkdown: vi.fn(),
  getAgentRun: vi.fn(),
  getAgentRuns: vi.fn(() => Promise.resolve([])),
  getImportedSources: vi.fn(() => Promise.resolve([])),
  getRagChunks: vi.fn(() => Promise.resolve([])),
  runAgentWorkflow: vi.fn(),
}));

describe("AgentDashboard smoke", () => {
  it("renders goal input", () => {
    render(<AgentDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByPlaceholderText("Example: Check payment module drift and prepare a full report.")).toBeInTheDocument();
  });
});
