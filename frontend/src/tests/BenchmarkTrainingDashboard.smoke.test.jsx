import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import BenchmarkTrainingDashboard from "../pages/BenchmarkTrainingDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  createBenchmarkSplit: vi.fn(),
  createDriftGuardDatasetFromBenchmark: vi.fn(),
  deleteBenchmarkDataset: vi.fn(),
  downloadTrainingExport: vi.fn(),
  exportTrainingDataset: vi.fn(),
  getBenchmarkDatasets: vi.fn(() => Promise.resolve([])),
  getBenchmarkExamples: vi.fn(() => Promise.resolve([])),
  getBenchmarkQuality: vi.fn(() => Promise.resolve(null)),
  getBenchmarkRegistry: vi.fn(() => Promise.resolve({
    cosqa: { name: "CosQA", purpose: "Code-text alignment", expected_formats: [".json"], output_task: "code_text_alignment" },
    snli: { name: "SNLI", purpose: "Contradiction detection", expected_formats: [".jsonl"], output_task: "contradiction_detection" },
  })),
  getTrainingExports: vi.fn(() => Promise.resolve([])),
  mergeTrainingData: vi.fn(),
  uploadBenchmarkDataset: vi.fn(),
}));

describe("BenchmarkTrainingDashboard smoke", () => {
  it("renders dashboard title", () => {
    render(<BenchmarkTrainingDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Benchmark and Training Data Pipeline")).toBeInTheDocument();
  });
});
