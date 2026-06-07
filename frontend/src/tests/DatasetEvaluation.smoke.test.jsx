import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DatasetEvaluation from "../components/DatasetEvaluation.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  buildTrainingDataset: vi.fn(),
  compareEvaluations: vi.fn(),
  deleteEvaluationResult: vi.fn(),
  deleteFeedback: vi.fn(),
  deleteSavedDataset: vi.fn(),
  evaluateSavedDataset: vi.fn(),
  exportCorrectedDataset: vi.fn(),
  exportLatestEvaluationJson: vi.fn(),
  exportLatestEvaluationMarkdown: vi.fn(),
  getAllFeedback: vi.fn(() => Promise.resolve([])),
  getDatasetLibrary: vi.fn(() => Promise.resolve([])),
  getEvaluationHistory: vi.fn(() => Promise.resolve([])),
  getEvaluationResult: vi.fn(),
  getFeedbackForEvaluation: vi.fn(),
  getFeedbackSummaryForEvaluation: vi.fn(),
  getLatestImpactGraph: vi.fn(),
  getLatestRootCauseReport: vi.fn(),
  getLatestTimeline: vi.fn(),
  getImpactGraphForEvaluation: vi.fn(),
  getRootCauseReportForEvaluation: vi.fn(),
  getSampleDataset: vi.fn(() => Promise.resolve([])),
  getSavedDataset: vi.fn(),
  getTimelineForEvaluation: vi.fn(),
  runDatasetEvaluation: vi.fn(),
  saveCaseFeedback: vi.fn(),
  saveUploadedDataset: vi.fn(),
  uploadDatasetEvaluate: vi.fn(),
  uploadDatasetPreview: vi.fn(),
  runHybridReasoning: vi.fn(),
}));

describe("DatasetEvaluation smoke", () => {
  it("renders dataset controls", () => {
    render(<DatasetEvaluation user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Dataset Evaluation")).toBeInTheDocument();
    expect(screen.getByText("Run Sample Evaluation")).toBeInTheDocument();
  });
});
