import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api.js";
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

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ValidationResearchDashboard smoke", () => {
  it("renders validation dashboard title", () => {
    render(<ValidationResearchDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Validation and Research Results")).toBeInTheDocument();
    expect(screen.getByText("Demo Readiness")).toBeInTheDocument();
  });

  it("shows a visible error when validation action fails", async () => {
    api.runFullSystemValidation.mockRejectedValueOnce(new Error("Validation failed."));

    render(<ValidationResearchDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);

    fireEvent.click(screen.getByText("Run Full System Validation"));

    await waitFor(() => {
      expect(screen.getByText("Validation failed.")).toBeInTheDocument();
    });
  });
});
