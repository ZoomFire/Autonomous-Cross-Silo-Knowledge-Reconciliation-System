import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MonitoringDashboard from "../components/MonitoringDashboard.jsx";

vi.mock("../api.js", async () => ({
  ...(await vi.importActual("../api.js")),
  createMonitoringRule: vi.fn(),
  deleteMonitoringAlert: vi.fn(),
  deleteMonitoringRule: vi.fn(),
  deleteMonitoringRun: vi.fn(),
  exportMonitoringAlertsJson: vi.fn(),
  exportMonitoringAlertsMarkdown: vi.fn(),
  getDatasetLibrary: vi.fn(() => Promise.resolve([])),
  getMonitoringAlerts: vi.fn(() => Promise.resolve([])),
  getMonitoringRules: vi.fn(() => Promise.resolve([])),
  getMonitoringRuns: vi.fn(() => Promise.resolve([])),
  runMonitoringRule: vi.fn(),
  updateMonitoringAlertStatus: vi.fn(),
}));

describe("MonitoringDashboard smoke", () => {
  it("renders monitoring title", () => {
    render(<MonitoringDashboard user={{ role: "admin" }} workspaceId="workspace-1" />);
    expect(screen.getByText("Proactive Drift Monitoring")).toBeInTheDocument();
  });
});
