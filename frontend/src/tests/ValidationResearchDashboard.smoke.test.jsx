import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ValidationResearchDashboard from "../pages/ValidationResearchDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  deleteValidationRun: vi.fn(),
  exportResearchReportMarkdown: vi.fn(),
  exportValidationMetricsCsv: vi.fn(),
  exportValidationResultsJson: vi.fn(),
  generateResearchReport: vi.fn(),
  getDatasetLibrary: vi.fn(() => Promise.resolve([])),
  getDemoReadiness: vi.fn(),
  getDemoScenarios: vi.fn(() => Promise.resolve([{ name: "Payment API Drift Demo", steps: [] }])),
  getResearchResults: vi.fn(() => Promise.resolve([])),
  getValidationRun: vi.fn(),
  getValidationRuns: vi.fn(() => Promise.resolve([])),
  runAblationStudy: vi.fn(),
  runBaselineComparison: vi.fn(),
  runDemoScenarioValidation: vi.fn(),
  runFullSystemValidation: vi.fn(),
  runRealDatasetValidation: vi.fn(),
}));

describe("ValidationResearchDashboard smoke", () => {
  it("renders validation dashboard title", () => {
    render(<ValidationResearchDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Validation and Research Results")).toBeInTheDocument();
    expect(screen.getByText("Demo Readiness")).toBeInTheDocument();
  });
});
