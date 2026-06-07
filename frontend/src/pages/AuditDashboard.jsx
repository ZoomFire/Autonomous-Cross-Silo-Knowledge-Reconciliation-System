import { useEffect, useMemo, useState } from "react";
import { Download, Eye, Trash2 } from "lucide-react";
import {
  deleteAuditEvent,
  exportAuditJson,
  exportAuditMarkdown,
  getAuditEvents,
  getAuditSummary,
  getComplianceRisk,
} from "../api.js";
import PermissionGuard from "../components/PermissionGuard.jsx";

const emptyFilters = { workspace_id: "", user_id: "", action: "", resource_type: "", status: "", severity: "" };
const securityActions = new Set(["permission_denied", "unauthorized_access", "login_failed", "invalid_token", "expired_token"]);

function Badge({ value }) {
  return <span className={`badge ${(value || "").toLowerCase()}`}>{value}</span>;
}

export default function AuditDashboard({ user, workspaceId }) {
  const [summary, setSummary] = useState(null);
  const [risk, setRisk] = useState(null);
  const [events, setEvents] = useState([]);
  const [filters, setFilters] = useState({ ...emptyFilters, workspace_id: workspaceId || "" });
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [error, setError] = useState("");

  const recentSecurityEvents = useMemo(
    () => events.filter((event) => securityActions.has(event.action)).slice(0, 8),
    [events],
  );

  async function loadAll(activeFilters = filters) {
    setError("");
    try {
      const [eventItems, summaryPayload, riskPayload] = await Promise.all([
        getAuditEvents(activeFilters),
        getAuditSummary(activeFilters.workspace_id || ""),
        getComplianceRisk(activeFilters.workspace_id || ""),
      ]);
      setEvents(eventItems);
      setSummary(summaryPayload);
      setRisk(riskPayload);
    } catch (err) {
      setError(err.message || "Unable to load audit dashboard.");
    }
  }

  useEffect(() => {
    const nextFilters = { ...filters, workspace_id: workspaceId || "" };
    setFilters(nextFilters);
    loadAll(nextFilters);
  }, [workspaceId]);

  function updateFilter(key, value) {
    setFilters({ ...filters, [key]: value });
  }

  function clearFilters() {
    const next = { ...emptyFilters, workspace_id: workspaceId || "" };
    setFilters(next);
    loadAll(next);
  }

  async function removeEvent(auditId) {
    if (!confirm("Are you sure you want to delete this audit event?")) return;
    try {
      await deleteAuditEvent(auditId);
      setSelectedEvent(null);
      await loadAll();
    } catch (err) {
      setError(err.message || "Audit event delete failed.");
    }
  }

  return (
    <PermissionGuard user={user} permission="manage_users" fallback={<section className="page"><div className="error-banner">Permission denied. Audit dashboard is available only for admins.</div></section>}>
      <section className="page">
        <div className="page-header">
          <div>
            <h2>Audit</h2>
            <p>Enterprise audit trail and compliance governance.</p>
          </div>
          <div className="header-actions">
            <button className="secondary-button" onClick={() => exportAuditJson(filters.workspace_id)}><Download size={17} />Export Audit JSON</button>
            <button className="secondary-button" onClick={() => exportAuditMarkdown(filters.workspace_id)}><Download size={17} />Export Audit Markdown</button>
          </div>
        </div>

        <section className="info-box">
          <strong>Enterprise Audit Trail</strong><br />
          Track user actions, permission failures, exports, deletions, monitoring events, and workspace governance activity.
        </section>
        {error && <div className="error-banner">{error}</div>}

        {summary && (
          <div className="dashboard-grid">
            <div className="metric-card compact"><span>Total Events</span><strong>{summary.total_events}</strong></div>
            <div className="metric-card compact"><span>Success</span><strong>{summary.success_events}</strong></div>
            <div className="metric-card compact"><span>Failed</span><strong>{summary.failed_events}</strong></div>
            <div className="metric-card compact"><span>Denied</span><strong>{summary.denied_events}</strong></div>
            <div className="metric-card compact"><span>Critical</span><strong>{summary.critical_events}</strong></div>
            <div className="metric-card compact"><span>High</span><strong>{summary.high_events}</strong></div>
            <div className="metric-card compact"><span>Exports</span><strong>{summary.export_events}</strong></div>
            <div className="metric-card compact"><span>Deletes</span><strong>{summary.delete_events}</strong></div>
          </div>
        )}

        {risk && (
          <section className="panel">
            <div className="section-heading">
              <h3>Compliance Risk</h3>
              <span className={`badge ${risk.risk_level.toLowerCase()}`}>{risk.risk_level} / {risk.risk_score}</span>
            </div>
            <div className="comparison-grid">
              <div><span>Risk Factors</span>{risk.risk_factors.map((item) => <p key={item}>{item}</p>)}</div>
              <div><span>Recommendations</span>{risk.recommendations.map((item) => <p key={item}>{item}</p>)}</div>
            </div>
          </section>
        )}

        <section className="panel">
          <div className="section-heading"><h3>Filters</h3></div>
          <div className="filters-grid">
            <label>Workspace<input value={filters.workspace_id} onChange={(event) => updateFilter("workspace_id", event.target.value)} placeholder="workspace id" /></label>
            <label>User<input value={filters.user_id} onChange={(event) => updateFilter("user_id", event.target.value)} placeholder="user id" /></label>
            <label>Action<input value={filters.action} onChange={(event) => updateFilter("action", event.target.value)} placeholder="run_evaluation" /></label>
            <label>Resource Type<input value={filters.resource_type} onChange={(event) => updateFilter("resource_type", event.target.value)} placeholder="dataset" /></label>
            <label>Status<select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}><option value="">All</option><option>success</option><option>failed</option><option>denied</option><option>warning</option></select></label>
            <label>Severity<select value={filters.severity} onChange={(event) => updateFilter("severity", event.target.value)}><option value="">All</option><option>Info</option><option>Low</option><option>Medium</option><option>High</option><option>Critical</option></select></label>
          </div>
          <div className="control-actions">
            <button className="primary-button" onClick={() => loadAll()}>Apply Filters</button>
            <button className="secondary-button" onClick={clearFilters}>Clear Filters</button>
          </div>
        </section>

        <section className="panel">
          <div className="section-heading"><h3>Recent Security Events</h3></div>
          {recentSecurityEvents.length === 0 ? <p className="empty-state">No recent security events.</p> : (
            <div className="table-wrap">
              <table><thead><tr><th>Time</th><th>User</th><th>Action</th><th>Status</th><th>Severity</th><th>Message</th></tr></thead><tbody>
                {recentSecurityEvents.map((event) => <tr key={event.audit_id}><td>{new Date(event.created_at).toLocaleString()}</td><td>{event.user_email}</td><td>{event.action}</td><td><Badge value={event.status} /></td><td><Badge value={event.severity} /></td><td>{event.message}</td></tr>)}
              </tbody></table>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="section-heading"><h3>Audit Events</h3><span className="source-badge">{events.length} events</span></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Time</th><th>User</th><th>Role</th><th>Action</th><th>Resource Type</th><th>Resource Name</th><th>Status</th><th>Severity</th><th>Message</th><th>Actions</th></tr></thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.audit_id}>
                    <td>{new Date(event.created_at).toLocaleString()}</td>
                    <td>{event.user_email || event.user_name}</td>
                    <td>{event.user_role}</td>
                    <td>{event.action}</td>
                    <td>{event.resource_type}</td>
                    <td>{event.resource_name}</td>
                    <td><Badge value={event.status} /></td>
                    <td><Badge value={event.severity} /></td>
                    <td>{event.message}</td>
                    <td><div className="row-actions"><button className="secondary-button" onClick={() => setSelectedEvent(event)}><Eye size={15} />View</button><button className="secondary-button danger-button" onClick={() => removeEvent(event.audit_id)}><Trash2 size={15} />Delete</button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {selectedEvent && (
          <section className="panel">
            <div className="section-heading"><h3>Audit Event Detail</h3><button className="secondary-button" onClick={() => setSelectedEvent(null)}>Close</button></div>
            <pre className="json-preview">{JSON.stringify(selectedEvent, null, 2)}</pre>
          </section>
        )}
      </section>
    </PermissionGuard>
  );
}
