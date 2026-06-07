import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import { exportLatestRootCauseJson, exportLatestRootCauseMarkdown } from "../api.js";
import HybridReasoningPanel from "./HybridReasoningPanel.jsx";

function entries(value = {}) {
  return Object.entries(value);
}

function DistributionTable({ title, distribution }) {
  return (
    <section className="panel">
      <div className="section-heading"><h3>{title}</h3></div>
      <div className="table-wrap">
        <table className="matrix-table">
          <thead><tr><th>Value</th><th>Count</th></tr></thead>
          <tbody>
            {entries(distribution).map(([key, value]) => <tr key={key}><td>{key}</td><td>{value}</td></tr>)}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function RootCauseDashboard({ report, onError, workspaceId }) {
  const [filters, setFilters] = useState({ priority: "all", source: "all", category: "all", owner: "all", effort: "all" });

  const filteredCases = useMemo(() => {
    return (report?.cases || []).filter((item) => {
      if (filters.priority !== "all" && item.priority_level !== filters.priority) return false;
      if (filters.source !== "all" && item.responsible_source !== filters.source) return false;
      if (filters.category !== "all" && item.root_cause_category !== filters.category) return false;
      if (filters.owner !== "all" && item.suggested_owner !== filters.owner) return false;
      if (filters.effort !== "all" && item.fix_effort !== filters.effort) return false;
      return true;
    });
  }, [report, filters]);

  if (!report) return null;

  const unique = (key) => Array.from(new Set(report.cases.map((item) => item[key]))).filter(Boolean);
  const update = (key, value) => setFilters({ ...filters, [key]: value });

  async function exportReport(exporter) {
    try {
      await exporter();
    } catch (err) {
      onError(err.message);
    }
  }

  return (
    <section className="root-cause-stack">
      <div className="dashboard-grid">
        <div className="metric-card compact"><span>Total Cases</span><strong>{report.total_cases}</strong></div>
        <div className="metric-card compact"><span>Drift Cases</span><strong>{report.drift_cases}</strong></div>
        <div className="metric-card compact"><span>Critical Priority</span><strong>{report.critical_priority_cases}</strong></div>
        <div className="metric-card compact"><span>High Priority</span><strong>{report.high_priority_cases}</strong></div>
        <div className="metric-card compact"><span>Avg Priority</span><strong>{report.average_priority_score}</strong></div>
      </div>

      <div className="matrix-grid">
        <DistributionTable title="Root Cause Distribution" distribution={report.root_cause_distribution} />
        <DistributionTable title="Responsible Source Distribution" distribution={report.responsible_source_distribution} />
        <DistributionTable title="Recommended Owner Distribution" distribution={report.recommended_owner_distribution} />
      </div>

      <HybridReasoningPanel taskType="root_cause_analysis" inputContext={report.cases?.[0] || { evidence: report }} workspaceId={workspaceId} />

      <section className="panel filters-panel">
        <div className="section-heading"><h3>Root Cause Filters</h3></div>
        <div className="filters-grid">
          <label>Priority<select value={filters.priority} onChange={(event) => update("priority", event.target.value)}><option value="all">All</option>{unique("priority_level").map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Source<select value={filters.source} onChange={(event) => update("source", event.target.value)}><option value="all">All</option>{unique("responsible_source").map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Category<select value={filters.category} onChange={(event) => update("category", event.target.value)}><option value="all">All</option>{unique("root_cause_category").map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Owner<select value={filters.owner} onChange={(event) => update("owner", event.target.value)}><option value="all">All</option>{unique("suggested_owner").map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Effort<select value={filters.effort} onChange={(event) => update("effort", event.target.value)}><option value="all">All</option>{unique("fix_effort").map((item) => <option key={item}>{item}</option>)}</select></label>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Root Cause Case Analysis</h3>
          <span className="source-badge">{filteredCases.length} shown</span>
        </div>
        <div className="case-results">
          {filteredCases.map((item) => (
            <article className="case-detail" key={item.case_id}>
              <div className="case-detail-header">
                <strong>{item.case_id} - {item.title}</strong>
                <div className="badge-row">
                  <span className={`badge ${item.priority_level.toLowerCase()}`}>{item.priority_level}</span>
                  <span className="badge info-badge">{item.responsible_source}</span>
                </div>
              </div>
              <div className="comparison-grid">
                <div><span>Root Cause</span><p>{item.root_cause_category}</p></div>
                <div><span>Suggested Owner</span><p>{item.suggested_owner}</p></div>
                <div><span>Priority Score</span><p>{item.priority_score}</p></div>
                <div><span>Fix Effort</span><p>{item.fix_effort}</p></div>
              </div>
              <p><strong>Risk impact:</strong> {item.risk_impact}</p>
              <p><strong>Recommended fix:</strong> {item.recommended_fix}</p>
              <ol>{item.action_plan.map((step) => <li key={step}>{step}</li>)}</ol>
            </article>
          ))}
        </div>
      </section>

      <section className="panel export-panel">
        <div>
          <h3>Export Root Cause Report</h3>
          <p>Download the latest root cause report as JSON or Markdown.</p>
        </div>
        <div className="control-actions">
          <button className="secondary-button" onClick={() => exportReport(exportLatestRootCauseJson)}><Download size={17} />Export Root Cause JSON</button>
          <button className="secondary-button" onClick={() => exportReport(exportLatestRootCauseMarkdown)}><Download size={17} />Export Root Cause Markdown</button>
        </div>
      </section>
    </section>
  );
}
