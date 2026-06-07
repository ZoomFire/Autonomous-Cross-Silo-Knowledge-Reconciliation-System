import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import IntegrationDashboard from "../pages/IntegrationDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  createIntegration: vi.fn(),
  deleteIntegration: vi.fn(),
  getExternalLinkedResources: vi.fn(() => Promise.resolve([])),
  getIncidents: vi.fn(() => Promise.resolve([])),
  getIntegrationHealthSummary: vi.fn(() => Promise.resolve({
    total_integrations: 0,
    enabled_integrations: 0,
    healthy_integrations: 0,
    error_integrations: 0,
    mock_integrations: 0,
    live_integrations: 0,
    recent_sync_failures: 0,
  })),
  getIntegrationSyncRecords: vi.fn(() => Promise.resolve([])),
  getIntegrations: vi.fn(() => Promise.resolve([])),
  getMockExternalItems: vi.fn(() => Promise.resolve([])),
  notifyIncidentExternal: vi.fn(),
  syncIncidentToExternal: vi.fn(),
  testIntegration: vi.fn(),
}));

describe("IntegrationDashboard smoke", () => {
  it("renders dashboard title", () => {
    render(<IntegrationDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("External Workflow Integrations")).toBeInTheDocument();
    expect(screen.getAllByText("Create Integration").length).toBeGreaterThan(0);
  });
});
