import { useEffect, useMemo, useState } from "react";
import { Download, PlayCircle, Trash2 } from "lucide-react";
import {
  createMonitoringRule,
  deleteMonitoringAlert,
  deleteMonitoringRule,
  deleteMonitoringRun,
  exportMonitoringAlertsJson,
  exportMonitoringAlertsMarkdown,
  getDatasetLibrary,
  getMonitoringAlerts,
  getMonitoringRules,
  getMonitoringRuns,
  runMonitoringRule,
  updateMonitoringAlertStatus,
} from "../api.js";
import PermissionGuard from "./PermissionGuard.jsx";

const defaultThresholds = {
  minimum_accuracy: 80,
  minimum_label_accuracy: 85,
  minimum_drift_type_accuracy: 75,
  minimum_severity_accuracy: 70,
  max_critical_cases: 0,
  max_high_cases: 2,
  max_average_priority_score: 70,
};

export default function MonitoringDashboard({ user, workspaceId }) {
  const [datasets, setDatasets] = useState([]);
  const [rules, setRules] = useState([]);
  const [runs, setRuns] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", dataset_id: "", description: "", enabled: true, thresholds: defaultThresholds });
  const [filters, setFilters] = useState({ status: "all", severity: "all", alertType: "all", dataset: "all" });

  useEffect(() => { refreshAll(); }, [workspaceId]);

  async function refreshAll() {
    try {
      const [datasetItems, ruleItems, runItems, alertItems] = await Promise.all([
        getDatasetLibrary(),
        getMonitoringRules(),
        getMonitoringRuns(),
        getMonitoringAlerts(),
      ]);
      setDatasets(datasetItems);
      setRules(ruleItems);
      setRuns(runItems);
      setAlerts(alertItems);
      if (!form.dataset_id && datasetItems[0]) setForm((current) => ({ ...current, dataset_id: datasetItems[0].dataset_id }));
    } catch (err) {
      setError(err.message);
    }
  }

  function setThreshold(key, value) {
    setForm({ ...form, thresholds: { ...form.thresholds, [key]: Number(value) } });
  }

  async function createRule() {
    if (!workspaceId) return setError("No workspace selected. Please create or select a workspace first.");
    if (!form.name.trim()) return setError("Rule name is required.");
    if (!form.dataset_id) return setError("Dataset is required.");
    setError("");
    try {
      await createMonitoringRule({
        ...form,
        alert_settings: {
          alert_on_accuracy_drop: true,
          alert_on_critical_drift: true,
          alert_on_high_priority_component: true,
          alert_on_regression: true,
        },
      });
      setForm({ name: "", dataset_id: form.dataset_id, description: "", enabled: true, thresholds: defaultThresholds });
      await refreshAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function runRule(ruleId) {
    try {
      await runMonitoringRule(ruleId);
      await refreshAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeRule(ruleId) {
    if (!confirm("Are you sure you want to delete this monitoring rule?")) return;
    await deleteMonitoringRule(ruleId);
    await refreshAll();
  }

  async function removeRun(runId) {
    if (!confirm("Are you sure you want to delete this monitoring run?")) return;
    await deleteMonitoringRun(runId);
    await refreshAll();
  }

  async function setAlertStatus(alertId, status) {
    await updateMonitoringAlertStatus(alertId, status);
    await refreshAll();
  }

  async function removeAlert(alertId) {
    if (!confirm("Are you sure you want to delete this alert?")) return;
    await deleteMonitoringAlert(alertId);
    await refreshAll();
  }

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    if (filters.status !== "all" && alert.status !== filters.status) return false;
    if (filters.severity !== "all" && alert.severity !== filters.severity) return false;
    if (filters.alertType !== "all" && alert.alert_type !== filters.alertType) return false;
    if (filters.dataset !== "all" && alert.dataset_name !== filters.dataset) return false;
    return true;
  }), [alerts, filters]);

  const summary = {
    totalRules: rules.length,
    enabledRules: rules.filter((rule) => rule.enabled).length,
    totalRuns: runs.length,
    openAlerts: alerts.filter((alert) => alert.status === "open").length,
    criticalAlerts: alerts.filter((alert) => alert.severity === "Critical").length,
    highAlerts: alerts.filter((alert) => alert.severity === "High").length,
    resolvedAlerts: alerts.filter((alert) => alert.status === "resolved").length,
  };

  const unique = (items) => Array.from(new Set(items)).filter(Boolean);

  return (
    <section className="page">
      <div className="page-header"><div><h2>Proactive Drift Monitoring</h2><p>Create local monitoring rules for saved datasets and manually run checks to detect drift, regressions, and risky components.</p></div></div>
      <section className="info-box">Monitoring runs are local and manual in Level 2.8. Save a dataset first, then create a watch rule for it.</section>
      {error && <div className="error-banner">{error}</div>}
      <div className="dashboard-grid">
        <div className="metric-card compact"><span>Total Rules</span><strong>{summary.totalRules}</strong></div>
        <div className="metric-card compact"><span>Enabled Rules</span><strong>{summary.enabledRules}</strong></div>
        <div className="metric-card compact"><span>Total Runs</span><strong>{summary.totalRuns}</strong></div>
        <div className="metric-card compact"><span>Open Alerts</span><strong>{summary.openAlerts}</strong></div>
        <div className="metric-card compact"><span>Critical Alerts</span><strong>{summary.criticalAlerts}</strong></div>
      </div>

      <PermissionGuard user={user} permission="create_monitoring_rule">
      <section className="panel control-panel">
        <h3>Create Monitoring Rule</h3>
        <div className="save-grid">
          <label>Rule Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label>Dataset<select value={form.dataset_id} onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}>{datasets.map((d) => <option key={d.dataset_id} value={d.dataset_id}>{d.name}</option>)}</select></label>
          <label>Description<input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
          <label>Enabled<input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /></label>
        </div>
        <div className="save-grid">
          {Object.entries(form.thresholds).map(([key, value]) => (
            <label key={key}>{key.replaceAll("_", " ")}<input type="number" value={value} onChange={(e) => setThreshold(key, e.target.value)} /></label>
          ))}
          <button className="primary-button" onClick={createRule} disabled={!workspaceId}>Create Monitoring Rule</button>
        </div>
      </section>
      </PermissionGuard>

      <section className="panel"><div className="section-heading"><h3>Monitoring Rules</h3></div><div className="table-wrap"><table><thead><tr><th>Name</th><th>Dataset</th><th>Enabled</th><th>Min Accuracy</th><th>Max Critical</th><th>Max Avg Priority</th><th>Created</th><th>Actions</th></tr></thead><tbody>{rules.map((rule) => <tr key={rule.rule_id}><td>{rule.name}</td><td>{rule.dataset_name}</td><td>{rule.enabled ? "Yes" : "No"}</td><td>{rule.thresholds.minimum_accuracy}</td><td>{rule.thresholds.max_critical_cases}</td><td>{rule.thresholds.max_average_priority_score}</td><td>{new Date(rule.created_at).toLocaleString()}</td><td><div className="row-actions"><PermissionGuard user={user} permission="run_evaluation"><button className="secondary-button" onClick={() => runRule(rule.rule_id)}><PlayCircle size={15}/>Run Check</button></PermissionGuard><PermissionGuard user={user} permission="delete_monitoring_rule"><button className="secondary-button danger-button" onClick={() => removeRule(rule.rule_id)}><Trash2 size={15}/>Delete</button></PermissionGuard></div></td></tr>)}</tbody></table></div></section>

      <section className="panel"><div className="section-heading"><h3>Monitoring Run History</h3></div><div className="table-wrap"><table><thead><tr><th>Run ID</th><th>Rule</th><th>Dataset</th><th>Created</th><th>Status</th><th>Accuracy</th><th>Critical</th><th>High</th><th>Avg Priority</th><th>Alerts</th><th>Actions</th></tr></thead><tbody>{runs.map((run) => <tr key={run.run_id}><td>{run.run_id.slice(0,8)}</td><td>{run.rule_name || run.rule_id.slice(0,8)}</td><td>{run.dataset_name}</td><td>{new Date(run.created_at).toLocaleString()}</td><td>{run.status}</td><td>{run.accuracy}%</td><td>{run.critical_cases}</td><td>{run.high_cases}</td><td>{run.average_priority_score}</td><td>{run.alerts_created}</td><td><PermissionGuard user={user} permission="delete_history"><button className="secondary-button danger-button" onClick={() => removeRun(run.run_id)}>Delete</button></PermissionGuard></td></tr>)}</tbody></table></div></section>

      <section className="panel">
        <div className="section-heading"><h3>Alert Dashboard</h3><PermissionGuard user={user} permission="export_reports"><div className="control-actions"><button className="secondary-button" disabled={!alerts.length} onClick={exportMonitoringAlertsJson}><Download size={15}/>Export JSON</button><button className="secondary-button" disabled={!alerts.length} onClick={exportMonitoringAlertsMarkdown}><Download size={15}/>Export Markdown</button></div></PermissionGuard></div>
        <div className="dashboard-grid"><div className="metric-card compact"><span>Total Alerts</span><strong>{alerts.length}</strong></div><div className="metric-card compact"><span>Open</span><strong>{summary.openAlerts}</strong></div><div className="metric-card compact"><span>Critical</span><strong>{summary.criticalAlerts}</strong></div><div className="metric-card compact"><span>High</span><strong>{summary.highAlerts}</strong></div><div className="metric-card compact"><span>Resolved</span><strong>{summary.resolvedAlerts}</strong></div></div>
        <div className="filters-grid">
          <label>Status<select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}><option value="all">All</option>{["open","acknowledged","resolved"].map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>Severity<select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}><option value="all">All</option>{unique(alerts.map((a) => a.severity)).map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>Alert Type<select value={filters.alertType} onChange={(e) => setFilters({ ...filters, alertType: e.target.value })}><option value="all">All</option>{unique(alerts.map((a) => a.alert_type)).map((x) => <option key={x}>{x}</option>)}</select></label>
          <label>Dataset<select value={filters.dataset} onChange={(e) => setFilters({ ...filters, dataset: e.target.value })}><option value="all">All</option>{unique(alerts.map((a) => a.dataset_name)).map((x) => <option key={x}>{x}</option>)}</select></label>
        </div>
        <div className="case-results">{filteredAlerts.map((alert) => <article className="case-detail mismatch" key={alert.alert_id}><div className="case-detail-header"><strong>{alert.title}</strong><div className="badge-row"><span className={`badge ${alert.severity.toLowerCase()}`}>{alert.severity}</span><span className={alert.status === "resolved" ? "badge passed" : alert.status === "acknowledged" ? "badge warning" : "badge failed"}>{alert.status}</span></div></div><p>{alert.message}</p><p><strong>Dataset:</strong> {alert.dataset_name} | <strong>Type:</strong> {alert.alert_type}</p><p><strong>Actual vs threshold:</strong> {alert.actual_value} / {alert.threshold_value}</p><p><strong>Recommended action:</strong> {alert.recommended_action}</p><p><strong>Related cases:</strong> {(alert.related_cases || []).join(", ") || "None"}</p><PermissionGuard user={user} permission="manage_alerts"><div className="row-actions"><button className="secondary-button" onClick={() => setAlertStatus(alert.alert_id, "acknowledged")}>Acknowledge</button><button className="secondary-button" onClick={() => setAlertStatus(alert.alert_id, "resolved")}>Resolve</button><button className="secondary-button" onClick={() => setAlertStatus(alert.alert_id, "open")}>Reopen</button><button className="secondary-button danger-button" onClick={() => removeAlert(alert.alert_id)}>Delete</button></div></PermissionGuard></article>)}</div>
      </section>
    </section>
  );
}
