import { Activity, AlertTriangle, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getObservabilityErrors, getObservabilityRequests, getObservabilitySummary, getPerformanceHealth } from "../api.js";

const emptySummary = {
  total_requests: 0,
  success_requests: 0,
  error_requests: 0,
  average_duration_ms: 0,
  slow_requests: 0,
  top_slow_endpoints: [],
  recent_errors: [],
};

function formatTime(value) {
  if (!value) return "Unknown";
  return new Date(value).toLocaleString();
}

function StatusBadge({ status }) {
  const className = status === "healthy" ? "success" : status === "degraded" ? "warning" : "neutral";
  return <span className={`badge ${className}`}>{status || "unknown"}</span>;
}

function CodeBadge({ code }) {
  const value = Number(code);
  const className = value >= 500 ? "failed" : value >= 400 ? "warning" : "success";
  return <span className={`badge ${className}`}>{code}</span>;
}

export default function ObservabilityDashboard() {
  const [summary, setSummary] = useState(emptySummary);
  const [performance, setPerformance] = useState(null);
  const [requests, setRequests] = useState([]);
  const [errors, setErrors] = useState([]);
  const [filters, setFilters] = useState({ path: "", status_code: "", slow_only: false });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const errorRate = useMemo(() => {
    if (!summary.total_requests) return 0;
    return ((summary.error_requests / summary.total_requests) * 100).toFixed(2);
  }, [summary]);

  async function refresh(nextFilters = filters) {
    setLoading(true);
    setError("");
    try {
      const [summaryData, performanceData, requestItems, errorItems] = await Promise.all([
        getObservabilitySummary(),
        getPerformanceHealth(),
        getObservabilityRequests(nextFilters),
        getObservabilityErrors(),
      ]);
      setSummary(summaryData);
      setPerformance(performanceData);
      setRequests(requestItems);
      setErrors(errorItems);
    } catch (err) {
      setError(err.message || "Unable to load observability data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <section className="page observability-page">
      <div className="page-header">
        <div>
          <h2>System Observability</h2>
          <p>Track request metrics, slow endpoints, backend errors, and performance health.</p>
        </div>
        <button className="secondary-button" onClick={() => refresh()} disabled={loading}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="evaluation-grid">
        <div className="metric-card compact"><span>Total requests</span><strong>{summary.total_requests}</strong></div>
        <div className="metric-card compact"><span>Success requests</span><strong>{summary.success_requests}</strong></div>
        <div className="metric-card compact"><span>Error requests</span><strong>{summary.error_requests}</strong></div>
        <div className="metric-card compact"><span>Average duration</span><strong>{summary.average_duration_ms} ms</strong></div>
        <div className="metric-card compact"><span>Slow requests</span><strong>{summary.slow_requests}</strong></div>
        <div className="metric-card compact"><span>Error rate</span><strong>{errorRate}%</strong></div>
      </div>

      <section className="panel observability-health">
        <div className="section-heading">
          <h3><Activity size={18} /> Performance Health</h3>
          <StatusBadge status={performance?.status} />
        </div>
        <div className="observability-health-grid">
          <div><span>Average duration</span><strong>{performance?.average_duration_ms ?? 0} ms</strong></div>
          <div><span>Slow request count</span><strong>{performance?.slow_request_count ?? 0}</strong></div>
          <div><span>Error rate</span><strong>{performance?.error_rate ?? 0}%</strong></div>
        </div>
        <ul className="recommendation-list">
          {(performance?.recommendations || []).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3><AlertTriangle size={18} /> Slow Endpoints</h3>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Path</th><th>Method</th><th>Average duration</th><th>Count</th></tr></thead>
            <tbody>
              {(summary.top_slow_endpoints || []).map((item) => (
                <tr key={`${item.method}-${item.path}`}>
                  <td>{item.path}</td>
                  <td>{item.method}</td>
                  <td><span className={item.average_duration_ms > 1000 ? "duration-warning" : ""}>{item.average_duration_ms} ms</span></td>
                  <td>{item.count}</td>
                </tr>
              ))}
              {!summary.top_slow_endpoints?.length && <tr><td colSpan="4">No slow endpoint metrics yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Recent Errors</h3>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>Request ID</th><th>Method</th><th>Path</th><th>Status code</th><th>Message</th><th>Error type</th></tr></thead>
            <tbody>
              {errors.slice(0, 10).map((item) => (
                <tr key={item.error_id}>
                  <td>{formatTime(item.timestamp)}</td>
                  <td className="mono-cell">{item.request_id}</td>
                  <td>{item.method}</td>
                  <td>{item.path}</td>
                  <td><CodeBadge code={item.status_code} /></td>
                  <td>{item.message}</td>
                  <td>{item.error_type}</td>
                </tr>
              ))}
              {!errors.length && <tr><td colSpan="7">No backend errors recorded.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Request Metrics</h3>
        </div>
        <div className="filter-row">
          <label>Path<input value={filters.path} onChange={(event) => updateFilter("path", event.target.value)} placeholder="/health" /></label>
          <label>Status code<input value={filters.status_code} onChange={(event) => updateFilter("status_code", event.target.value)} placeholder="500" /></label>
          <label className="checkbox-label"><input type="checkbox" checked={filters.slow_only} onChange={(event) => updateFilter("slow_only", event.target.checked)} />Slow only</label>
          <button className="secondary-button" onClick={() => refresh(filters)} disabled={loading}><Search size={16} />Apply</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>Method</th><th>Path</th><th>Status</th><th>Duration</th><th>Request ID</th></tr></thead>
            <tbody>
              {requests.slice(0, 50).map((item) => (
                <tr key={`${item.request_id}-${item.timestamp}`}>
                  <td>{formatTime(item.timestamp)}</td>
                  <td>{item.method}</td>
                  <td>{item.path}</td>
                  <td><CodeBadge code={item.status_code} /></td>
                  <td><span className={item.slow ? "duration-warning" : ""}>{item.duration_ms} ms</span></td>
                  <td className="mono-cell">{item.request_id}</td>
                </tr>
              ))}
              {!requests.length && <tr><td colSpan="6">No request metrics recorded.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
