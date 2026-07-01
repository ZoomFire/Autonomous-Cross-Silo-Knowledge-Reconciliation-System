import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api.js";
import LLMSettingsDashboard from "../pages/LLMSettingsDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  createPromptTemplate: vi.fn(),
  deletePromptTemplate: vi.fn(),
  exportReasoningTraceMarkdown: vi.fn(),
  getHybridResults: vi.fn(() => Promise.resolve([
    {
      result_id: "result-12345678",
      trace_id: "trace-12345678",
      task_type: "contradiction_detection",
      approval_status: "pending",
      comparison: { agreement: true },
      final_result: { label: "contradiction" },
      created_at: "2026-06-30T17:01:34Z",
    },
  ])),
  getLLMSettings: vi.fn(() => Promise.resolve([])),
  getPromptTemplates: vi.fn(() => Promise.resolve([])),
  getReasoningTrace: vi.fn(),
  getReasoningTraces: vi.fn(() => Promise.resolve([])),
  saveLLMSettings: vi.fn(),
  updateHybridApproval: vi.fn(() => Promise.resolve({ approval_status: "approved" })),
  updateLLMSettings: vi.fn(),
  updatePromptTemplate: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LLMSettingsDashboard", () => {
  it("shows feedback after approving a hybrid result", async () => {
    render(<LLMSettingsDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);

    await screen.findByText("result-1");
    fireEvent.click(screen.getByTitle("Approve hybrid result"));

    await waitFor(() => {
      expect(api.updateHybridApproval).toHaveBeenCalledWith("result-12345678", { approval_status: "approved", approved_by_user: true });
      expect(screen.getByText("Hybrid result approved.")).toBeInTheDocument();
    });
  });
});
