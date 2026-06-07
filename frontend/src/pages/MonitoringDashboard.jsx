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
  getSampleDataset,
  getMonitoringAlerts,
  getMonitoringRules,
  getMonitoringRuns,
  runMonitoringRule,
  saveUploadedDataset,
  updateMonitoringAlertStatus,
  updateMonitoringRule,
} from "../api.js";

const defaultForm = {
  name: "",
  dataset_id: "",
  description: "",
  enabled: true,
  thresholds: {
    minimum_accuracy: 0.8,
    minimum_label_accuracy: 0.85,
    minimum_drift_type_accuracy: 0.75,
    minimum_severity_accuracy: 0.7,
    max_critical_cases: 0,
    max_high_cases: 2,
    max_average_priority_score: 70,
  },
  alert_settings: {
    alert_on_accuracy_drop: true,
    alert_on_critical_drift: true,
    alert_on_high_priority_component: true,
    alert_on_regression: true,
  },
};

function shortId(value = "") {
  return value.slice(0, 8);
}

function badgeClass(value = "") {
  return `badge ${value.toLowerCase()}`;
}

function countBy(items, key, value) {
  return items.filter((item) => item[key] === value).length;
}

export default function MonitoringDashboard() {
  const [datasets, setDatasets] = useState([]);
  const [rules, setRules] = useState([]);
  const [runs, setRuns] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [form, setForm] = useState(defaultForm);
  const [editingRuleId, setEditingRuleId] = useState("");
  const [filters, setFilters] = useState({ status: "all", severity: "all", alertType: "all", dataset: "all" });
  const [lastRunResult, setLastRunResult] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    refreshAll();
  }, []);

  async function refreshAll() {
    await Promise.all([refreshDatasets(), refreshRules(), refreshRuns(), refreshAlerts()]);
  }

  async function refreshDatasets() {
    try { setDatasets(await getDatasetLibrary()); } catch { setDatasets([]); }
  }

  async function refreshRules() {
    try { setRules(await getMonitoringRules()); } catch { setRules([]); }
  }

  async function refreshRuns() {
    try { setRuns(await getMonitoringRuns()); } catch { setRuns([]); }
  }

  async function refreshAlerts() {
    try { setAlerts(await getMonitoringAlerts()); } catch { setAlerts([]); }
  }

  async function createSampleSavedDataset() {
    setError("");
    setLoading(true);
    try {
      const sampleCases = await getSampleDataset();
      const blob = new Blob([JSON.stringify(sampleCases, null, 2)], { type: "application/json" });
      const file = new File([blob], "driftguard-sample-monitoring-dataset.json", { type: "application/json" });
      const saved = await saveUploadedDataset(file, "Sample Monitoring Dataset", "Built-in sample dataset saved for monitoring rules.", "1.0");
      await refreshDatasets();
      setForm((current) => ({ ...current, dataset_id: saved.dataset_id }));
      setSuccess("Sample dataset saved. It is now selected for the monitoring rule.");
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function showError(message) {
    setSuccess("");
    setError(message || "Monitoring action failed.");
  }

  function updateThreshold(key, value) {
    setForm({ ...form, thresholds: { ...form.thresholds, [key]: value } });
  }

  function updateAlertSetting(key, checked) {
    setForm({ ...form, alert_settings: { ...form.alert_settings, [key]: checked } });
  }

  function validateForm() {
    if (!form.name.trim()) return "Rule name is required.";
    if (!form.dataset_id) return "Dataset is required.";
    if (Object.values(form.thresholds).some((value) => Number.isNaN(Number(value)))) {
      return "Thresholds must be numbers.";
    }
    return "";
  }

  function normalizedForm() {
    return {
      ...form,
      thresholds: Object.fromEntries(Object.entries(form.thresholds).map(([key, value]) => [key, Number(value)])),
    };
  }

  async function submitRule() {
    const validationError = validateForm();
    if (validationError) {
      showError(validationError);
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (editingRuleId) {
        await updateMonitoringRule(editingRuleId, normalizedForm());
        setSuccess("Monitoring rule updated.");
      } else {
        await createMonitoringRule(normalizedForm());
        setSuccess("Monitoring rule created.");
      }
      setForm(defaultForm);
      setEditingRuleId("");
      await refreshRules();
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function editRule(rule) {
    setEditingRuleId(rule.rule_id);
    setForm({
      name: rule.name,
      dataset_id: rule.dataset_id,
      description: rule.description || "",
      enabled: rule.enabled,
      thresholds: rule.thresholds,
      alert_settings: rule.alert_settings,
    });
  }

  async function removeRule(ruleId) {
    setError("");
    try {
      await deleteMonitoringRule(ruleId);
      await refreshRules();
      setSuccess("Monitoring rule deleted.");
    } catch (err) {
      showError(err.message);
    }
  }

  async function runRule(ruleId) {
    setError("");
    setLoading(true);
    try {
      const result = await runMonitoringRule(ruleId);
      setLastRunResult(result);
      await Promise.all([refreshRuns(), refreshAlerts()]);
      setSuccess(`Monitoring check completed with ${result.alerts.length} alert(s).`);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function removeRun(runId) {
    try {
      await deleteMonitoringRun(runId);
      await refreshRuns();
      setSuccess("Monitoring run deleted.");
    } catch (err) {
      showError(err.message);
    }
  }

  async function setAlertStatus(alertId, status) {
    try {
      await updateMonitoringAlertStatus(alertId, status);
      await refreshAlerts();
      setSuccess(`Alert marked ${status}.`);
    } catch (err) {
      showError(err.message);
    }
  }

  async function removeAlert(alertId) {
    try {
      await deleteMonitoringAlert(alertId);
      await refreshAlerts();
      setSuccess("Alert deleted.");
    } catch (err) {
      showError(err.message);
    }
  }

  async function exportAlerts(exporter) {
    if (!alerts.length) {
      showError("No alerts available to export.");
      return;
    }
    try {
      await exporter();
    } catch (err) {
      showError(err.message);
    }
  }

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    if (filters.status !== "all" && alert.status !== filters.status) return false;
    if (filters.severity !== "all" && alert.severity !== filters.severity) return false;
    if (filters.alertType !== "all" && alert.alert_type !== filters.alertType) return false;
    if (filters.dataset !== "all" && alert.dataset_id !== filters.dataset) return false;
    return true;
  }), [alerts, filters]);

  const unique = (items) => Array.from(new Set(items)).filter(Boolean);
  const summary = {
    totalRules: rules.length,
    enabledRules: rules.filter((rule) => rule.enabled).length,
    totalRuns: runs.length,
    openAlerts: countBy(alerts, "status", "open"),
    criticalAlerts: countBy(alerts, "severity", "Critical"),
    highAlerts: countBy(alerts, "severity", "High"),
    resolvedAlerts: countBy(alerts, "status", "resolved"),
  };

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h2>Monitoring</h2>
          <p>Local drift watches for saved datasets, manual checks, threshold alerts, and alert history.</p>
        </div>
      </div>

      <section className="info-box">
        <strong>Proactive Drift Monitoring</strong><br />
        Create local monitoring rules for saved datasets and manually run checks to detect drift, regressions, and risky components.
      </section>

      {error && <div className="error-banner">{error}</div>}
      {success && <div className="success-banner">{success}</div>}

      <div className="dashboard-grid">
        <div className="metric-card compact"><span>Total Rules</span><strong>{summary.totalRules}</strong></div>
        <div className="metric-card compact"><span>Enabled Rules</span><strong>{summary.enabledRules}</strong></div>
        <div className="metric-card compact"><span>Total Runs</span><strong>{summary.totalRuns}</strong></div>
        <div className="metric-card compact"><span>Open Alerts</span><strong>{summary.openAlerts}</strong></div>
      </div>

      <section className="panel monitoring-form">
        <div className="section-heading"><h3>{editingRuleId ? "Edit Monitoring Rule" : "Create Monitoring Rule"}</h3></div>
        {datasets.length === 0 && (
          <div className="warning-box">
            <p>No saved datasets were found. Create one from the built-in sample dataset, or save an uploaded dataset from Dataset Evaluation.</p>
            <button className="secondary-button" onClick={createSampleSavedDataset} disabled={loading}>Create Sample Saved Dataset</button>
          </div>
        )}
        <div className="save-grid">
          <label>Rule Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Critical Payment Drift Watch" /></label>
          <label>Saved Dataset<select value={form.dataset_id} onChange={(event) => setForm({ ...form, dataset_id: event.target.value })}><option value="">Select dataset</option>{datasets.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.name}</option>)}</select></label>
          <label>Description<input value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Watch this benchmark for drift" /></label>
          <label className="checkbox-label"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} /> Enabled</label>
        </div>
        <div className="filters-grid">
          {Object.entries(form.thresholds).map(([key, value]) => (
            <label key={key}>{key.replaceAll("_", " ")}<input value={value} onChange={(event) => updateThreshold(key, event.target.value)} /></label>
          ))}
        </div>
        <div className="monitoring-checks">
          {Object.entries(form.alert_settings).map(([key, value]) => (
            <label className="checkbox-label" key={key}><input type="checkbox" checked={value} onChange={(event) => updateAlertSetting(key, event.target.checked)} /> {key.replaceAll("_", " ")}</label>
          ))}
        </div>
        <div className="control-actions">
          <button className="primary-button" onClick={submitRule} disabled={loading}>{editingRuleId ? "Update Monitoring Rule" : "Create Monitoring Rule"}</button>
          {editingRuleId && <button className="secondary-button" onClick={() => { setEditingRuleId(""); setForm(defaultForm); }}>Cancel Edit</button>}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Monitoring Rules</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Rule</th><th>Dataset</th><th>Status</th><th>Min Accuracy</th><th>Max Critical</th><th>Max Priority</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>{rules.map((rule) => (
              <tr key={rule.rule_id}>
                <td>{rule.name}</td><td>{rule.dataset_name}</td><td><span className={rule.enabled ? "badge passed" : "badge neutral"}>{rule.enabled ? "Enabled" : "Disabled"}</span></td>
                <td>{rule.thresholds.minimum_accuracy}</td><td>{rule.thresholds.max_critical_cases}</td><td>{rule.thresholds.max_average_priority_score}</td><td>{new Date(rule.created_at).toLocaleString()}</td>
                <td><div className="row-actions"><button className="secondary-button" onClick={() => runRule(rule.rule_id)} disabled={loading}><PlayCircle size={16} />Run Check</button><button className="secondary-button" onClick={() => editRule(rule)}>Edit</button><button className="secondary-button danger-button" onClick={() => removeRule(rule.rule_id)}><Trash2 size={16} />Delete</button></div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        {rules.length === 0 && <p className="empty-state">No monitoring rules yet.</p>}
      </section>

      {lastRunResult && <section className="panel insights-panel"><div className="section-heading"><h3>Latest Monitoring Result</h3></div><p>{lastRunResult.run.summary}</p><p className="empty-state">Run {shortId(lastRunResult.run.run_id)} created {lastRunResult.alerts.length} alert(s).</p></section>}

      <section className="panel">
        <div className="section-heading"><h3>Monitoring Run History</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Run ID</th><th>Rule</th><th>Dataset</th><th>Created</th><th>Status</th><th>Accuracy</th><th>Critical</th><th>High</th><th>Avg Priority</th><th>Alerts</th><th>Actions</th></tr></thead>
            <tbody>{runs.map((run) => (
              <tr key={run.run_id}><td>{shortId(run.run_id)}</td><td>{run.rule_name || shortId(run.rule_id)}</td><td>{run.dataset_name}</td><td>{new Date(run.created_at).toLocaleString()}</td><td>{run.status}</td><td>{run.accuracy}%</td><td>{run.critical_cases}</td><td>{run.high_cases}</td><td>{run.average_priority_score}</td><td>{run.alerts_created}</td><td><button className="secondary-button danger-button" onClick={() => removeRun(run.run_id)}>Delete</button></td></tr>
            ))}</tbody>
          </table>
        </div>
        {runs.length === 0 && <p className="empty-state">No monitoring runs yet.</p>}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Alert Dashboard</h3>
          <div className="control-actions">
            <button className="secondary-button" onClick={() => exportAlerts(exportMonitoringAlertsJson)} disabled={!alerts.length}><Download size={16} />Export Alerts JSON</button>
            <button className="secondary-button" onClick={() => exportAlerts(exportMonitoringAlertsMarkdown)} disabled={!alerts.length}><Download size={16} />Export Alerts Markdown</button>
          </div>
        </div>
        <div className="dashboard-grid">
          <div className="metric-card compact"><span>Total Alerts</span><strong>{alerts.length}</strong></div>
          <div className="metric-card compact"><span>Open</span><strong>{summary.openAlerts}</strong></div>
          <div className="metric-card compact"><span>Critical</span><strong>{summary.criticalAlerts}</strong></div>
          <div className="metric-card compact"><span>High</span><strong>{summary.highAlerts}</strong></div>
        </div>
        <div className="filters-grid">
          <label>Status<select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="all">All</option>{unique(alerts.map((alert) => alert.status)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Severity<select value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}><option value="all">All</option>{unique(alerts.map((alert) => alert.severity)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Alert Type<select value={filters.alertType} onChange={(event) => setFilters({ ...filters, alertType: event.target.value })}><option value="all">All</option>{unique(alerts.map((alert) => alert.alert_type)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Dataset<select value={filters.dataset} onChange={(event) => setFilters({ ...filters, dataset: event.target.value })}><option value="all">All</option>{unique(alerts.map((alert) => alert.dataset_id)).map((id) => <option key={id} value={id}>{alerts.find((alert) => alert.dataset_id === id)?.dataset_name}</option>)}</select></label>
        </div>
        <div className="case-results">
          {filteredAlerts.map((alert) => (
            <article className="case-detail" key={alert.alert_id}>
              <div className="case-detail-header"><strong>{alert.title}</strong><div className="badge-row"><span className={badgeClass(alert.severity)}>{alert.severity}</span><span className={badgeClass(alert.status)}>{alert.status}</span></div></div>
              <p>{alert.dataset_name} | {alert.alert_type}</p>
              <p>{alert.message}</p>
              <p><strong>Metric:</strong> {alert.metric_name} | <strong>Actual:</strong> {alert.actual_value} | <strong>Threshold:</strong> {alert.threshold_value}</p>
              <p><strong>Related cases:</strong> {(alert.related_cases || []).join(", ") || "None"}</p>
              <p><strong>Recommended action:</strong> {alert.recommended_action}</p>
              <p className="empty-state">{new Date(alert.created_at).toLocaleString()}</p>
              <div className="row-actions">
                <button className="secondary-button" onClick={() => setAlertStatus(alert.alert_id, "acknowledged")}>Acknowledge</button>
                <button className="secondary-button" onClick={() => setAlertStatus(alert.alert_id, "resolved")}>Resolve</button>
                <button className="secondary-button" onClick={() => setAlertStatus(alert.alert_id, "open")}>Reopen</button>
                <button className="secondary-button danger-button" onClick={() => removeAlert(alert.alert_id)}>Delete</button>
              </div>
            </article>
          ))}
        </div>
        {filteredAlerts.length === 0 && <p className="empty-state">No alerts match the current filters.</p>}
      </section>
    </section>
  );
}
