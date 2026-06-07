import { BarChart3, Calculator, Download, FileText, Play, RefreshCw, RotateCcw, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  advanceDemoStep,
  calculateExecutiveROI,
  disableDemoMode,
  enableDemoMode,
  exportExecutiveReportMarkdown,
  generateExecutiveReport,
  getDemoScenarios,
  getDemoState,
  getExecutiveMetrics,
  getExecutiveReports,
  resetDemoData,
  seedExecutiveDemoData,
} from "../api.js";

const defaultAssumptions = {
  manual_review_hours_per_case: 1.5,
  average_engineer_hourly_cost: 40,
  incident_cost_per_critical: 500,
  incident_cost_per_high: 250,
  automation_time_saved_percentage: 60,
};

function Badge({ value }) {
  const key = String(value || "Low").toLowerCase();
  const tone = key === "critical" || key === "high" ? "failed" : key === "medium" ? "warning" : key === "healthy" ? "success" : "neutral";
  return <span className={`badge ${tone}`}>{value}</span>;
}

function Metric({ label, value }) {
  return <div className="metric-card compact"><span>{label}</span><strong>{value ?? 0}</strong></div>;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

export default function ExecutiveDashboard({ user, workspaceId }) {
  const [metrics, setMetrics] = useState(null);
  const [roi, setRoi] = useState(null);
  const [reports, setReports] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [demoState, setDemoState] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState("Payment API Drift Demo");
  const [assumptions, setAssumptions] = useState(defaultAssumptions);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canReport = ["admin", "engineer", "reviewer"].includes(user?.role);
  const canDemo = ["admin", "engineer"].includes(user?.role);
  const canReset = user?.role === "admin";

  const activeScenario = useMemo(
    () => scenarios.find((item) => item.name === (demoState?.scenario_name || selectedScenario)) || scenarios[0],
    [scenarios, demoState?.scenario_name, selectedScenario],
  );

  async function refresh() {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const [nextMetrics, nextReports, nextScenarios, nextDemoState] = await Promise.all([
        getExecutiveMetrics(workspaceId),
        getExecutiveReports(workspaceId),
        getDemoScenarios(),
        getDemoState(workspaceId),
      ]);
      setMetrics(nextMetrics);
      setReports(nextReports);
      setScenarios(nextScenarios);
      setDemoState(nextDemoState);
      setSelectedScenario(nextDemoState?.scenario_name || nextScenarios[0]?.name || "Payment API Drift Demo");
    } catch (err) {
      setError(err.message || "Unable to load executive dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [workspaceId]);

  async function runRoi() {
    const result = await calculateExecutiveROI({ workspace_id: workspaceId, assumptions });
    setRoi(result);
    setMessage("ROI calculated.");
  }

  async function createReport() {
    const result = await generateExecutiveReport({ workspace_id: workspaceId, assumptions });
    setMessage("Executive report generated.");
    await refresh();
    setRoi(result.report?.roi || roi);
  }

  async function enableDemo() {
    const state = await enableDemoMode({ workspace_id: workspaceId, scenario_name: selectedScenario });
    setDemoState(state);
    setMessage("Demo mode enabled.");
  }

  async function disableDemo() {
    const state = await disableDemoMode({ workspace_id: workspaceId });
    setDemoState(state);
    setMessage("Demo mode disabled.");
  }

  async function advanceStep() {
    const state = await advanceDemoStep(workspaceId);
    setDemoState(state);
    setMessage("Demo step advanced.");
  }

  async function seedDemo() {
    await seedExecutiveDemoData(workspaceId);
    setMessage("Executive demo data seeded.");
    await refresh();
  }

  async function resetDemo() {
    if (!confirm("Reset demo state? User accounts and normal workspace data will not be deleted.")) return;
    const state = await resetDemoData(workspaceId);
    setDemoState(state);
    setMessage("Demo state reset.");
    await refresh();
  }

  const summary = metrics?.summary || {};
  const risk = metrics?.risk || {};
  const operations = metrics?.operations || {};

  return (
    <section className="page executive-page">
      {demoState?.enabled && <div className="success-banner">Demo Mode Active: {demoState.scenario_name}</div>}
      <div className="page-header">
        <div>
          <h2>Executive Overview</h2>
          <p>Summarize architectural drift risk, incidents, model health, compliance, integrations, and estimated ROI.</p>
        </div>
        <button className="secondary-button" onClick={refresh} disabled={loading}><RefreshCw size={16} />Refresh</button>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <div className="dashboard-grid">
        <Metric label="Datasets" value={summary.datasets || 0} />
        <Metric label="Evaluations" value={summary.evaluations || 0} />
        <Metric label="Drift cases" value={summary.drift_cases || 0} />
        <Metric label="Critical drift" value={summary.critical_drift_cases || 0} />
      </div>
      <div className="dashboard-grid">
        <Metric label="Open incidents" value={summary.open_incidents || 0} />
        <Metric label="Resolved incidents" value={summary.resolved_incidents || 0} />
        <Metric label="Alerts" value={summary.alerts || 0} />
        <Metric label="External syncs" value={summary.external_syncs || 0} />
      </div>

      <div className="incident-automation-grid">
        <div className="panel">
          <div className="section-heading"><h3><BarChart3 size={18} /> Risk Summary</h3></div>
          <div className="report-grid">
            <div><span>Drift risk score</span><strong>{risk.drift_risk_score || 0}</strong></div>
            <div><span>Security</span><strong><Badge value={risk.security_risk_level || "Low"} /></strong></div>
            <div><span>Model health</span><strong><Badge value={risk.model_health_risk || "Low"} /></strong></div>
            <div><span>Compliance</span><strong><Badge value={risk.compliance_risk || "Low"} /></strong></div>
          </div>
        </div>
        <div className="panel">
          <div className="section-heading"><h3>Operations Metrics</h3></div>
          <div className="report-grid">
            <div><span>Resolution hours</span><strong>{operations.average_resolution_time_hours || 0}</strong></div>
            <div><span>Review completion</span><strong>{operations.review_completion_rate || 0}%</strong></div>
            <div><span>Automation rate</span><strong>{operations.automation_rate || 0}%</strong></div>
            <div><span>Sync success</span><strong>{operations.external_sync_success_rate || 0}%</strong></div>
          </div>
        </div>
        <div className="panel">
          <div className="section-heading"><h3>Recommendations</h3></div>
          {(metrics?.recommendations || []).map((item) => <div className="agent-log-row" key={item}><span>{item}</span></div>)}
        </div>
      </div>

      <div className="incident-layout">
        <div className="panel incident-form">
          <div className="section-heading"><h3><Calculator size={18} /> ROI Calculator</h3></div>
          {Object.keys(defaultAssumptions).map((key) => (
            <label key={key}>{key}<input type="number" value={assumptions[key]} onChange={(event) => setAssumptions({ ...assumptions, [key]: Number(event.target.value) })} /></label>
          ))}
          <button className="primary-button" onClick={runRoi} type="button"><Calculator size={16} />Calculate ROI</button>
        </div>
        <div className="panel">
          <div className="section-heading"><h3>ROI Estimate</h3></div>
          <div className="report-grid">
            <div><span>Manual hours</span><strong>{roi?.estimated_manual_hours || 0}</strong></div>
            <div><span>Automated hours</span><strong>{roi?.estimated_automated_hours || 0}</strong></div>
            <div><span>Hours saved</span><strong>{roi?.estimated_hours_saved || 0}</strong></div>
            <div><span>Cost saved</span><strong>${roi?.estimated_cost_saved || 0}</strong></div>
            <div><span>Drift cost avoided</span><strong>${roi?.estimated_drift_cost_avoided || 0}</strong></div>
            <div><span>Total value</span><strong>${roi?.estimated_total_value || 0}</strong></div>
          </div>
          {roi?.roi_summary && <p className="report-summary">{roi.roi_summary}</p>}
        </div>
      </div>

      <div className="panel">
        <div className="section-heading"><h3>Top Risky Components</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Component</th><th>Risk score</th><th>Case count</th><th>Severity</th></tr></thead>
            <tbody>
              {(metrics?.top_risky_components || []).map((item) => (
                <tr key={`${item.component}-${item.risk_score}`}><td>{item.component}</td><td>{item.risk_score}</td><td>{item.case_count}</td><td><Badge value={item.severity} /></td></tr>
              ))}
              {(metrics?.top_risky_components || []).length === 0 && <tr><td colSpan="4">No risky components detected yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="incident-layout">
        <div className="panel">
          <div className="section-heading">
            <h3><FileText size={18} /> Executive Reports</h3>
            {canReport && <button className="primary-button" onClick={createReport} type="button"><FileText size={16} />Generate Executive Report</button>}
          </div>
          {reports.map((report) => (
            <div className="agent-log-row" key={report.report_id}>
              <span>{report.title}</span>
              <small>{formatDate(report.created_at)}</small>
              <button className="secondary-button" onClick={() => exportExecutiveReportMarkdown(report.report_id)} type="button"><Download size={16} />Export Markdown</button>
            </div>
          ))}
          {reports.length === 0 && <p className="empty-state">No executive reports generated yet.</p>}
        </div>

        <div className="panel">
          <div className="section-heading"><h3><Sparkles size={18} /> Demo Mode</h3></div>
          <label className="incident-form">Scenario<select value={selectedScenario} onChange={(event) => setSelectedScenario(event.target.value)}>
            {scenarios.map((scenario) => <option key={scenario.name} value={scenario.name}>{scenario.name}</option>)}
          </select></label>
          <p className="report-summary">Current step: {demoState?.current_step || 0}</p>
          <div className="button-row">
            {canDemo && <button className="secondary-button" onClick={enableDemo} type="button"><Play size={16} />Enable Demo Mode</button>}
            {canDemo && <button className="secondary-button" onClick={advanceStep} type="button">Advance Step</button>}
            {canDemo && <button className="secondary-button" onClick={seedDemo} type="button">Seed Executive Demo Data</button>}
            {canDemo && <button className="secondary-button" onClick={disableDemo} type="button">Disable Demo Mode</button>}
            {canReset && <button className="secondary-button danger" onClick={resetDemo} type="button"><RotateCcw size={16} />Reset Demo Data</button>}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="section-heading"><h3>Guided Walkthrough</h3></div>
        {(activeScenario?.steps || []).map((step, index) => (
          <div className="agent-log-row" key={step}>
            <span>{demoState?.completed_steps?.includes(step) ? "Done" : index === (demoState?.current_step || 0) ? "Current" : "Pending"}</span>
            <p>{step}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
