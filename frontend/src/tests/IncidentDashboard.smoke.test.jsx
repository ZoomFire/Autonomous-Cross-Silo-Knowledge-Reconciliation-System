import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import IncidentDashboard from "../pages/IncidentDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  addIncidentComment: vi.fn(),
  assignIncident: vi.fn(),
  checkIncidentEscalations: vi.fn(),
  createEscalationRule: vi.fn(),
  createIncident: vi.fn(),
  createIncidentWebhook: vi.fn(),
  deleteIncident: vi.fn(),
  exportIncidentMarkdown: vi.fn(),
  getEscalationRules: vi.fn(() => Promise.resolve([])),
  getIncident: vi.fn(),
  getIncidentNotificationLogs: vi.fn(() => Promise.resolve([])),
  getIncidentSummary: vi.fn(() => Promise.resolve({ total: 0, open: 0, resolved: 0, closed: 0, by_status: {}, by_severity: {} })),
  getIncidentWebhooks: vi.fn(() => Promise.resolve([])),
  getIncidents: vi.fn(() => Promise.resolve([])),
  testIncidentWebhook: vi.fn(),
  updateIncidentStatus: vi.fn(),
}));

describe("IncidentDashboard smoke", () => {
  it("renders incident workspace", () => {
    render(<IncidentDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Incident Management")).toBeInTheDocument();
    expect(screen.getByText("New Incident")).toBeInTheDocument();
    expect(screen.getByText("Incident Queue")).toBeInTheDocument();
  });
});
