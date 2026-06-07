import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import { exportLatestImpactGraphJson } from "../api.js";

export default function ImpactGraphDashboard({ report, onError }) {
  const [filters, setFilters] = useState({ component: "all", nodeType: "all", relationship: "all", severity: "all" });
  const unique = (items) => Array.from(new Set(items)).filter(Boolean);
  const update = (key, value) => setFilters({ ...filters, [key]: value });

  const nodes = useMemo(() => (report?.nodes || []).filter((node) => {
    if (filters.component !== "all" && node.component !== filters.component) return false;
    if (filters.nodeType !== "all" && node.type !== filters.nodeType) return false;
    return true;
  }), [report, filters]);

  const edges = useMemo(() => (report?.edges || []).filter((edge) => {
    if (filters.relationship !== "all" && edge.relationship !== filters.relationship) return false;
    if (filters.severity !== "all" && edge.severity !== filters.severity) return false;
    return true;
  }), [report, filters]);

  if (!report) return null;
  const highest = report.most_risky_components[0]?.component || "None";
  const exportReport = async () => {
    try { await exportLatestImpactGraphJson(); } catch (err) { onError(err.message); }
  };

  return (
    <section className="root-cause-stack">
      <div className="dashboard-grid">
        <div className="metric-card compact"><span>Total Nodes</span><strong>{report.total_nodes}</strong></div>
        <div className="metric-card compact"><span>Total Edges</span><strong>{report.total_edges}</strong></div>
        <div className="metric-card compact"><span>Affected Components</span><strong>{report.affected_components.length}</strong></div>
        <div className="metric-card compact"><span>Highest Risk</span><strong>{highest}</strong></div>
      </div>
      <section className="panel insights-panel"><div className="section-heading"><h3>Impact Summary</h3></div><ul>{report.impact_summary.map((item) => <li key={item}>{item}</li>)}</ul></section>
      <section className="panel">
        <div className="section-heading"><h3>Most Risky Components</h3></div>
        <div className="table-wrap"><table><thead><tr><th>Component</th><th>Risk Score</th><th>Risk Level</th><th>Case Count</th><th>Critical</th><th>High</th></tr></thead><tbody>{report.most_risky_components.map((item) => <tr key={item.component}><td>{item.component}</td><td>{item.risk_score}</td><td><span className={`badge ${item.risk_level.toLowerCase()}`}>{item.risk_level}</span></td><td>{item.case_count}</td><td>{item.critical_cases}</td><td>{item.high_cases}</td></tr>)}</tbody></table></div>
      </section>
      <section className="panel filters-panel">
        <div className="section-heading"><h3>Impact Graph Filters</h3></div>
        <div className="filters-grid">
          <label>Component<select value={filters.component} onChange={(event) => update("component", event.target.value)}><option value="all">All</option>{unique(report.nodes.map((node) => node.component)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Node Type<select value={filters.nodeType} onChange={(event) => update("nodeType", event.target.value)}><option value="all">All</option>{unique(report.nodes.map((node) => node.type)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Relationship<select value={filters.relationship} onChange={(event) => update("relationship", event.target.value)}><option value="all">All</option>{unique(report.edges.map((edge) => edge.relationship)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Severity<select value={filters.severity} onChange={(event) => update("severity", event.target.value)}><option value="all">All</option>{unique(report.edges.map((edge) => edge.severity)).map((item) => <option key={item}>{item}</option>)}</select></label>
        </div>
      </section>
      <section className="panel"><div className="section-heading"><h3>Graph Relationships</h3></div><div className="table-wrap"><table><thead><tr><th>From</th><th>Relationship</th><th>To</th><th>Severity</th><th>Case ID</th><th>Description</th></tr></thead><tbody>{edges.map((edge) => <tr key={edge.edge_id}><td>{edge.from}</td><td>{edge.relationship}</td><td>{edge.to}</td><td>{edge.severity}</td><td>{edge.case_id}</td><td>{edge.description}</td></tr>)}</tbody></table></div></section>
      <section className="panel"><div className="section-heading"><h3>Graph Nodes</h3></div><div className="table-wrap"><table><thead><tr><th>Node Label</th><th>Type</th><th>Component</th><th>Risk Score</th><th>Case IDs</th></tr></thead><tbody>{nodes.map((node) => <tr key={node.node_id}><td>{node.label}</td><td>{node.type}</td><td>{node.component}</td><td>{node.risk_score}</td><td>{node.case_ids.join(", ")}</td></tr>)}</tbody></table></div></section>
      <section className="panel export-panel"><div><h3>Export Impact Graph</h3><p>Download impact graph as JSON.</p></div><button className="secondary-button" onClick={exportReport}><Download size={17} />Export Impact Graph JSON</button></section>
    </section>
  );
}
