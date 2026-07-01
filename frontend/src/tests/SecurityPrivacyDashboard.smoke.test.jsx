import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import SecurityPrivacyDashboard from "../pages/SecurityPrivacyDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  approveWorkspaceDeleteRequest: vi.fn(),
  createWorkspaceDeleteRequest: vi.fn(),
  exportWorkspaceData: vi.fn(),
  getPrivacySettings: vi.fn(() => Promise.resolve({ workspace_id: "workspace-1" })),
  getSecurityEvents: vi.fn(() => Promise.resolve([])),
  getSecuritySummary: vi.fn(() => Promise.resolve({ security_risk_level: "Low" })),
  getWorkspaceDeleteRequests: vi.fn(() => Promise.resolve([])),
  updatePrivacySettings: vi.fn(),
}));

describe("SecurityPrivacyDashboard smoke", () => {
  it("renders dashboard title", () => {
    render(<SecurityPrivacyDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Security and Privacy Controls")).toBeInTheDocument();
  });
});
