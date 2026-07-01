import { useEffect, useMemo, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import ManualAnalysis from "./components/ManualAnalysis.jsx";
import DatasetEvaluation from "./components/DatasetEvaluation.jsx";
import DriftHistory from "./components/DriftHistory.jsx";
import MonitoringDashboard from "./components/MonitoringDashboard.jsx";
import UserProfile from "./components/UserProfile.jsx";
import WorkspaceSwitcher from "./components/WorkspaceSwitcher.jsx";
import AuditDashboard from "./pages/AuditDashboard.jsx";
import AgentDashboard from "./pages/AgentDashboard.jsx";
import BenchmarkTrainingDashboard from "./pages/BenchmarkTrainingDashboard.jsx";
import ConnectorDashboard from "./pages/ConnectorDashboard.jsx";
import CrossSiloSearch from "./pages/CrossSiloSearch.jsx";
import ExecutiveDashboard from "./pages/ExecutiveDashboard.jsx";
import LLMSettingsDashboard from "./pages/LLMSettingsDashboard.jsx";
import IncidentDashboard from "./pages/IncidentDashboard.jsx";
import IntegrationDashboard from "./pages/IntegrationDashboard.jsx";
import ModelTrainingDashboard from "./pages/ModelTrainingDashboard.jsx";
import ObservabilityDashboard from "./pages/ObservabilityDashboard.jsx";
import SecurityPrivacyDashboard from "./pages/SecurityPrivacyDashboard.jsx";
import SystemAdminDashboard from "./pages/SystemAdminDashboard.jsx";
import ValidationResearchDashboard from "./pages/ValidationResearchDashboard.jsx";
import { getSelectedWorkspaceId, getWorkspaces, setSelectedWorkspaceId } from "./api.js";

const PUBLIC_USER = {
  user_id: "public-user",
  name: "Public User",
  email: "local@driftguard",
  role: "admin",
};

export default function App() {
  const [activePage, setActivePage] = useState("manual");
  const user = PUBLIC_USER;
  const [workspaces, setWorkspaces] = useState([]);
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState(getSelectedWorkspaceId());

  const currentWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.workspace_id === currentWorkspaceId),
    [workspaces, currentWorkspaceId],
  );

  async function loadWorkspaces(preferredWorkspaceId = getSelectedWorkspaceId()) {
    const items = await getWorkspaces();
    setWorkspaces(items);
    const selected = items.find((workspace) => workspace.workspace_id === preferredWorkspaceId)?.workspace_id || items[0]?.workspace_id || "";
    setCurrentWorkspaceId(selected);
    setSelectedWorkspaceId(selected);
    return selected;
  }

  async function boot() {
    try {
      await loadWorkspaces();
    } catch {
      setWorkspaces([]);
    }
  }

  useEffect(() => {
    boot();
  }, []);

  async function refreshWorkspaceAfterCreate(workspaceId) {
    await loadWorkspaces(workspaceId);
  }

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onNavigate={setActivePage} user={user} />
      <main className="main-content">
        <header className="top-nav">
          <WorkspaceSwitcher
            user={user}
            workspaces={workspaces}
            currentWorkspaceId={currentWorkspaceId}
            onWorkspaceChange={setCurrentWorkspaceId}
            onWorkspaceCreated={refreshWorkspaceAfterCreate}
          />
          <UserProfile user={user} workspace={currentWorkspace} />
        </header>
        {!currentWorkspaceId && (
          <div className="error-banner">No workspace selected. Create or select a workspace before using datasets, evaluations, and monitoring.</div>
        )}
        {activePage === "manual" && <ManualAnalysis user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "dataset" && <DatasetEvaluation user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "training-data" && <BenchmarkTrainingDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "models" && <ModelTrainingDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "executive" && <ExecutiveDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "validation" && <ValidationResearchDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "connectors" && <ConnectorDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "search" && <CrossSiloSearch user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "agent" && <AgentDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "ai-settings" && <LLMSettingsDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "monitoring" && <MonitoringDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "incidents" && <IncidentDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "integrations" && <IntegrationDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "history" && <DriftHistory />}
        {activePage === "audit" && <AuditDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "observability" && <ObservabilityDashboard user={user} />}
        {activePage === "security" && <SecurityPrivacyDashboard user={user} workspaceId={currentWorkspaceId} />}
        {activePage === "system" && <SystemAdminDashboard user={user} />}
      </main>
    </div>
  );
}
