import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ExecutiveDashboard from "../pages/ExecutiveDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  advanceDemoStep: vi.fn(),
  calculateExecutiveROI: vi.fn(),
  disableDemoMode: vi.fn(),
  enableDemoMode: vi.fn(),
  exportExecutiveReportMarkdown: vi.fn(),
  generateExecutiveReport: vi.fn(),
  getDemoScenarios: vi.fn(() => Promise.resolve([{ name: "Payment API Drift Demo", steps: ["Import demo sources"] }])),
  getDemoState: vi.fn(() => Promise.resolve({ enabled: false, scenario_name: "", current_step: 0, completed_steps: [] })),
  getExecutiveMetrics: vi.fn(() => Promise.resolve({
    summary: {},
    risk: {},
    operations: {},
    top_risky_components: [],
    recommendations: ["Maintain current monitoring cadence."],
  })),
  getExecutiveReports: vi.fn(() => Promise.resolve([])),
  resetDemoData: vi.fn(),
  seedExecutiveDemoData: vi.fn(),
}));

describe("ExecutiveDashboard smoke", () => {
  it("renders executive title", () => {
    render(<ExecutiveDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Executive Overview")).toBeInTheDocument();
    expect(screen.getByText("ROI Calculator")).toBeInTheDocument();
  });
});
