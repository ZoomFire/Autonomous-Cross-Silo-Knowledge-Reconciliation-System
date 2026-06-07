import { BarChart3, Download, FileText, Play, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  deleteValidationRun,
  exportResearchReportMarkdown,
  exportValidationMetricsCsv,
  exportValidationResultsJson,
  generateResearchReport,
  getDatasetLibrary,
  getDemoReadiness,
  getDemoScenarios,
  getResearchResults,
  getValidationRun,
  getValidationRuns,
  runAblationStudy,
  runBaselineComparison,
  runDemoScenarioValidation,
  runFullSystemValidation,
  runRealDatasetValidation,
} from "../api.js";

function Badge({ value }) {
  const key = String(value || "unknown").toLowerCase();
  const tone = key === "completed" || key === "success" ? "success" : key === "failed" ? "failed" : key === "partial" || key === "running" ? "warning" : "neutral";
  return <span className={`badge ${tone}`}>{value || "unknown"}</span>;
}

function Metric({ label, value }) {
  return <div className="metric-card compact"><span>{label}</span><strong>{value ?? 0}</strong></div>;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

function Bars({ chart }) {
  const max = Math.max(...(chart?.values || [1]), 1);
  return (
    <div className="validation-bars">
      {(chart?.labels || []).map((label, index) => (
        <div key={label} className="validation-bar-row">
          <span>{label}</span>
          <div><strong style={{ width: `${((chart.values[index] || 0) / max) * 100}%` }} /></div>
          <small>{chart.values[index] || 0}</small>
        </div>
      ))}
    </div>
  );
}

export default function ValidationResearchDashboard({ user, workspaceId }) {
  const [datasets, setDatasets] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [researchResults, setResearchResults] = useState([]);
  const [baseline, setBaseline] = useState(null);
  const [ablation, setAblation] = useState(null);
  const [form, setForm] = useState({ dataset_id: "", name: "Payment Drift Real Dataset Validation", scenario_name: "Payment API Drift Demo" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const canRun = ["admin", "engineer", "reviewer"].includes(user?.role);
  const canDelete = user?.role === "admin";

  async function refresh() {
    if (!workspaceId) return;
    setError("");
    try {
      const [nextDatasets, nextScenarios, nextRuns, nextResults] = await Promise.all([
        getDatasetLibrary().catch(() => []),
        getDemoScenarios(),
        getValidationRuns(workspaceId),
        getResearchResults(workspaceId),
      ]);
      setDatasets(nextDatasets);
      setScenarios(nextScenarios);
      setRuns(nextRuns);
      setResearchResults(nextResults);
      setForm((current) => ({
        ...current,
        dataset_id: current.dataset_id || nextDatasets[0]?.dataset_id || "",
        scenario_name: current.scenario_name || nextScenarios[0]?.name || "Payment API Drift Demo",
      }));
    } catch (err) {
      setError(err.message || "Unable to load validation dashboard.");
    }
  }

  useEffect(() => {
    refresh();
  }, [workspaceId]);

  async function checkReadiness() {
    setReadiness(await getDemoReadiness(workspaceId));
  }

  async function runReal() {
    const result = await runRealDatasetValidation({ workspace_id: workspaceId, dataset_id: form.dataset_id, name: form.name });
    setSelected(result);
    setMessage("Real dataset validation completed.");
    await refresh();
  }

  async function runFull() {
    const result = await runFullSystemValidation({ workspace_id: workspaceId, name: "Full DriftGuard System Validation" });
    setSelected(result);
    setMessage("Full system validation completed.");
    await refresh();
  }

  async function runDemo() {
    const result = await runDemoScenarioValidation({ workspace_id: workspaceId, scenario_name: form.scenario_name });
    setSelected(result);
    setMessage("Demo scenario validation completed.");
    await refresh();
  }

  async function viewRun(validationId) {
    setSelected(await getValidationRun(validationId));
  }

  async function removeRun(validationId) {
    if (!confirm("Delete this validation run?")) return;
    await deleteValidationRun(validationId);
    setSelected(null);
    await refresh();
  }

  async function makeResearch(validationId) {
    const result = await generateResearchReport(validationId);
    setMessage("Research report generated.");
    await refresh();
    return result;
  }

  async function compareBaseline() {
    setBaseline(await runBaselineComparison({ workspace_id: workspaceId, dataset_id: form.dataset_id }));
  }

  async function runAblation() {
    setAblation(await runAblationStudy({ workspace_id: workspaceId, dataset_id: form.dataset_id }));
  }

  const metrics = selected?.metrics || {};
  const chartData = selected?.chart_data || selected?.report?.chart_data || {};

  return (
    <section className="page validation-page">
      <div className="page-header">
        <div>
          <h2>Validation and Research Results</h2>
          <p>Run end-to-end validation on real or demo data, generate research-ready metrics, compare baselines, run ablation studies, and export final reports.</p>
        </div>
        <button className="secondary-button" onClick={refresh}><RefreshCw size={16} />Refresh</button>
      </div>
      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <div className="section-heading"><h3>Demo Readiness</h3><button className="secondary-button" onClick={checkReadiness}>Check Demo Readiness</button></div>
        <div className="dashboard-grid">
          <Metric label="Ready" value={readiness?.ready_for_demo ? "Yes" : "No"} />
          <Metric label="Demo score" value={readiness?.score || 0} />
          <Metric label="Passed checks" value={(readiness?.checks || []).filter((item) => item.passed).length} />
          <Metric label="Missing" value={(readiness?.missing_items || []).length} />
        </div>
        {(readiness?.recommendations || []).map((item) => <p className="empty-state" key={item}>{item}</p>)}
      </div>

      <div className="incident-automation-grid">
        <div className="panel incident-form">
          <div className="section-heading"><h3><Play size={18} /> Real Dataset Validation</h3></div>
          <label>Dataset<select value={form.dataset_id} onChange={(event) => setForm({ ...form, dataset_id: event.target.value })}>{datasets.map((dataset) => <option key={dataset.dataset_id} value={dataset.dataset_id}>{dataset.name}</option>)}</select></label>
          <label>Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          {canRun && <button className="primary-button" disabled={!form.dataset_id} onClick={runReal}>Run Real Dataset Validation</button>}
        </div>
        <div className="panel">
          <div className="section-heading"><h3>Full System Validation</h3></div>
          {canRun && <button className="primary-button" onClick={runFull}>Run Full System Validation</button>}
        </div>
        <div className="panel incident-form">
          <div className="section-heading"><h3>Demo Scenario Validation</h3></div>
          <label>Scenario<select value={form.scenario_name} onChange={(event) => setForm({ ...form, scenario_name: event.target.value })}>{scenarios.map((scenario) => <option key={scenario.name} value={scenario.name}>{scenario.name}</option>)}</select></label>
          {canRun && <button className="primary-button" onClick={runDemo}>Run Demo Scenario Validation</button>}
        </div>
      </div>

      <div className="panel">
        <div className="section-heading"><h3>Validation Runs</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Started</th><th>Accuracy</th><th>Drift</th><th>Value</th><th>Actions</th></tr></thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.validation_id}>
                  <td>{run.name}</td><td>{run.validation_type}</td><td><Badge value={run.status} /></td><td>{formatDate(run.started_at)}</td>
                  <td>{run.summary?.accuracy ?? run.metrics?.evaluation?.accuracy ?? 0}</td><td>{run.summary?.drift_cases ?? run.metrics?.drift?.total_drift_cases ?? 0}</td><td>${run.summary?.estimated_total_value ?? run.metrics?.business?.estimated_total_value ?? 0}</td>
                  <td className="button-row">
                    <button className="secondary-button" onClick={() => viewRun(run.validation_id)}>View</button>
                    {canRun && <button className="secondary-button" onClick={() => makeResearch(run.validation_id)}><FileText size={16} />Research</button>}
                    <button className="secondary-button" onClick={() => exportValidationResultsJson(run.validation_id)}><Download size={16} />JSON</button>
                    <button className="secondary-button" onClick={() => exportValidationMetricsCsv(run.validation_id)}>CSV</button>
                    <button className="secondary-button" onClick={() => exportResearchReportMarkdown(run.validation_id)}>Markdown</button>
                    {canDelete && <button className="secondary-button danger" onClick={() => removeRun(run.validation_id)}><Trash2 size={16} />Delete</button>}
                  </td>
                </tr>
              ))}
              {runs.length === 0 && <tr><td colSpan="8">No validation runs yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <>
          <div className="dashboard-grid">
            <Metric label="Accuracy" value={metrics.evaluation?.accuracy || 0} />
            <Metric label="Label accuracy" value={metrics.evaluation?.label_accuracy || 0} />
            <Metric label="Critical drift" value={metrics.drift?.critical_drift_cases || 0} />
            <Metric label="Incidents created" value={metrics.incidents?.incidents_created || 0} />
          </div>
          <div className="incident-automation-grid">
            <div className="panel"><div className="section-heading"><h3><BarChart3 size={18} /> Accuracy</h3></div><Bars chart={chartData.accuracy_bar_chart} /></div>
            <div className="panel"><div className="section-heading"><h3>Severity Distribution</h3></div><Bars chart={chartData.severity_distribution_pie} /></div>
            <div className="panel"><div className="section-heading"><h3>ROI Values</h3></div><Bars chart={chartData.roi_chart} /></div>
          </div>
        </>
      )}

      <div className="incident-layout">
        <div className="panel">
          <div className="section-heading"><h3>Baseline Comparison</h3><button className="secondary-button" disabled={!form.dataset_id || !canRun} onClick={compareBaseline}>Run Baseline Comparison</button></div>
          {(baseline?.baseline_results || []).map((item) => <div className="agent-log-row" key={item.mode}><span>{item.mode}</span><small>Accuracy {item.accuracy}</small><p>{item.notes}</p></div>)}
          {baseline?.summary && <p className="report-summary">{baseline.summary}</p>}
        </div>
        <div className="panel">
          <div className="section-heading"><h3>Ablation Study</h3><button className="secondary-button" disabled={!form.dataset_id || !canRun} onClick={runAblation}>Run Ablation Study</button></div>
          {(ablation?.ablation_results || []).map((item) => <div className="agent-log-row" key={item.configuration}><span>{item.configuration}</span><small>Accuracy {item.accuracy}</small><p>{item.notes}</p></div>)}
        </div>
      </div>

      <div className="panel">
        <div className="section-heading"><h3>Research Results History</h3></div>
        {researchResults.map((item) => <div className="agent-log-row" key={item.research_result_id}><span>{item.result_type}</span><small>{formatDate(item.created_at)}</small><p>{item.title}</p></div>)}
        {researchResults.length === 0 && <p className="empty-state">No research results generated yet.</p>}
      </div>
    </section>
  );
}
