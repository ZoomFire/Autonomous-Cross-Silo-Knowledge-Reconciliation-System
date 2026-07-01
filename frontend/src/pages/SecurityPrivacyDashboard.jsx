import { Download, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  approveWorkspaceDeleteRequest,
  createWorkspaceDeleteRequest,
  exportWorkspaceData,
  getPrivacySettings,
  getSecurityEvents,
  getSecuritySummary,
  getWorkspaceDeleteRequests,
  updatePrivacySettings,
} from "../api.js";

const defaultSettings = {
  privacy_mode_enabled: true,
  redact_exports: true,
  data_retention_days: 90,
  allow_workspace_export: true,
  allow_workspace_delete_request: true,
};

function Badge({ value }) {
  const key = String(value || "Low").toLowerCase();
  const className = key === "critical" || key === "rejected" ? "failed" : key === "high" ? "orange" : key === "medium" || key === "pending" ? "warning" : "success";
  return <span className={`badge ${className}`}>{value}</span>;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

export default function SecurityPrivacyDashboard({ user, workspaceId }) {
  const [summary, setSummary] = useState(null);
  const [settings, setSettings] = useState(defaultSettings);
  const [deleteRequests, setDeleteRequests] = useState([]);
  const [events, setEvents] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canAdmin = user?.role === "admin";
  const cards = useMemo(() => [
    ["Total users", summary?.total_users ?? 0],
    ["Locked accounts", summary?.locked_accounts ?? 0],
    ["Failed logins 24h", summary?.failed_logins_24h ?? 0],
    ["Rate limit events 24h", summary?.rate_limit_events_24h ?? 0],
    ["Sensitive data events 24h", summary?.sensitive_data_events_24h ?? 0],
  ], [summary]);

  async function refresh() {
    if (!canAdmin || !workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextSettings, nextRequests, nextEvents] = await Promise.all([
        getSecuritySummary(),
        getPrivacySettings(workspaceId),
        getWorkspaceDeleteRequests(),
        getSecurityEvents(),
      ]);
      setSummary(nextSummary);
      setSettings({ ...defaultSettings, ...nextSettings });
      setDeleteRequests(nextRequests);
      setEvents(nextEvents);
    } catch (err) {
      setError(err.message || "Unable to load security data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [workspaceId, canAdmin]);

  async function saveSettings() {
    setError("");
    setMessage("");
    try {
      setSettings(await updatePrivacySettings({ ...settings, workspace_id: workspaceId }));
      setMessage("Privacy settings saved.");
    } catch (err) {
      setError(err.message || "Unable to save privacy settings.");
    }
  }

  async function requestDelete() {
    if (!confirm("Are you sure you want to create a workspace deletion request?")) return;
    setError("");
    setMessage("");
    try {
      await createWorkspaceDeleteRequest(workspaceId);
      setMessage("Workspace deletion request created.");
      await refresh();
    } catch (err) {
      setError(err.message || "Unable to create delete request.");
    }
  }

  async function approveRequest(requestId) {
    await approveWorkspaceDeleteRequest(requestId);
    await refresh();
  }

  if (!canAdmin) {
    return <section className="page"><div className="error-banner">Permission denied. Security settings are available only for admins.</div></section>;
  }

  return (
    <section className="page security-page">
      <div className="page-header">
        <div>
          <h2>Security and Privacy Controls</h2>
          <p>Manage sensitive data protection, workspace privacy settings, and data export/delete requests.</p>
        </div>
        <button className="secondary-button" onClick={refresh} disabled={loading}><RefreshCw size={16} />Refresh</button>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <div className="evaluation-grid">
        {cards.map(([label, value]) => <div className="metric-card compact" key={label}><span>{label}</span><strong>{value}</strong></div>)}
        <div className="metric-card compact"><span>Security risk level</span><strong><Badge value={summary?.security_risk_level || "Low"} /></strong></div>
      </div>

      <section className="panel">
        <div className="section-heading"><h3>Privacy Settings</h3></div>
        <div className="filter-row security-controls">
          {["privacy_mode_enabled", "redact_exports", "allow_workspace_export", "allow_workspace_delete_request"].map((key) => (
            <label className="checkbox-label" key={key}>
              <input type="checkbox" checked={Boolean(settings[key])} onChange={(event) => setSettings({ ...settings, [key]: event.target.checked })} />
              {key.replaceAll("_", " ")}
            </label>
          ))}
          <label>Data retention days<input type="number" min="1" value={settings.data_retention_days} onChange={(event) => setSettings({ ...settings, data_retention_days: Number(event.target.value) })} /></label>
          <button className="primary-button" onClick={saveSettings}>Save Privacy Settings</button>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Workspace Data Controls</h3></div>
        <div className="button-row">
          <button className="secondary-button" onClick={() => exportWorkspaceData(workspaceId)} disabled={!settings.allow_workspace_export}><Download size={16} />Export Workspace Data</button>
          <button className="secondary-button" onClick={requestDelete} disabled={!settings.allow_workspace_delete_request}><Trash2 size={16} />Request Workspace Deletion</button>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Delete Requests</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Request ID</th><th>Workspace</th><th>Requested by</th><th>Status</th><th>Created at</th><th>Actions</th></tr></thead>
            <tbody>
              {deleteRequests.map((item) => (
                <tr key={item.delete_request_id}>
                  <td className="mono-cell">{item.delete_request_id}</td>
                  <td>{item.workspace_id}</td>
                  <td>{item.requested_by}</td>
                  <td><Badge value={item.status} /></td>
                  <td>{formatDate(item.created_at)}</td>
                  <td>{item.status === "pending" && <button className="secondary-button" onClick={() => approveRequest(item.delete_request_id)}>Approve</button>}</td>
                </tr>
              ))}
              {!deleteRequests.length && <tr><td colSpan="6">No delete requests found.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Security Events</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Status</th><th>Severity</th><th>Message</th></tr></thead>
            <tbody>
              {events.slice(0, 50).map((item) => (
                <tr key={item.audit_id}>
                  <td>{formatDate(item.created_at)}</td>
                  <td>{item.user_email || item.user_name}</td>
                  <td>{item.action}</td>
                  <td><Badge value={item.status} /></td>
                  <td>{item.severity}</td>
                  <td>{item.message}</td>
                </tr>
              ))}
              {!events.length && <tr><td colSpan="6">No security events found.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
