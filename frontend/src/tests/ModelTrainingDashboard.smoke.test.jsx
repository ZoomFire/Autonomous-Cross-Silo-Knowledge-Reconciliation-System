import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ModelTrainingDashboard from "../pages/ModelTrainingDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  compareModelExperiments: vi.fn(),
  deleteModelExperiment: vi.fn(),
  deployModelExperiment: vi.fn(),
  exportModelExperimentMarkdown: vi.fn(),
  getBenchmarkDatasets: vi.fn(() => Promise.resolve([])),
  getDeployedModels: vi.fn(() => Promise.resolve([])),
  getModelExperiment: vi.fn(),
  getModelLeaderboard: vi.fn(() => Promise.resolve([])),
  getTrainingExports: vi.fn(() => Promise.resolve([])),
  predictWithMLModel: vi.fn(),
  rollbackDeployedModel: vi.fn(),
  trainModelExperiment: vi.fn(),
}));

describe("ModelTrainingDashboard smoke", () => {
  it("renders dashboard title", () => {
    render(<ModelTrainingDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Model Training Sandbox")).toBeInTheDocument();
  });
});
