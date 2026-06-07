import { Bell, GitBranch, Link2, PlugZap, RefreshCw, Send, Trash2, Workflow } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  createIntegration,
  deleteIntegration,
  getExternalLinkedResources,
  getIncidents,
  getIntegrationHealthSummary,
  getIntegrationSyncRecords,
  getIntegrations,
  getMockExternalItems,
  notifyIncidentExternal,
  syncIncidentToExternal,
  testIntegration,
} from "../api.js";

const integrationTypes = ["jira", "github_issues", "slack", "teams", "generic_webhook"];

function Badge({ value }) {
  const key = String(value || "unknown").toLowerCase();
  const tone = key === "healthy" || key === "success" || key === "live"
    ? "success"
    : key === "error" || key === "failed"
      ? "failed"
      : key === "degraded"
        ? "warning"
        : "neutral";
  return <span className={`badge ${tone}`}>{value || "unknown"}</span>;
}

function Metric({ label, value }) {
  return <div className="metric-card compact"><span>{label}</span><strong>{value ?? 0}</strong></div>;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

function defaultConfig(type) {
  if (type === "jira") return { base_url: "", project_key: "DG", email: "", api_token: "" };
  if (type === "github_issues") return { repo_owner: "", repo_name: "", token: "" };
  return { webhook_url: "", secret: "" };
}

export default function IntegrationDashboard({ user, workspaceId }) {
  const [summary, setSummary] = useState(null);
  const [integrations, setIntegrations] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [records, setRecords] = useState([]);
  const [links, setLinks] = useState([]);
  const [mockItems, setMockItems] = useState([]);
  const [form, setForm] = useState({ name: "Demo Jira Mock", integration_type: "jira", mode: "mock", enabled: true, config: defaultConfig("jira") });
  const [syncForm, setSyncForm] = useState({ incident_id: "", integration_id: "" });
  const [syncResult, setSyncResult] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canManage = ["admin", "engineer"].includes(user?.role);
  const canDelete = user?.role === "admin";

  const selectedIntegration = useMemo(
    () => integrations.find((item) => item.integration_id === syncForm.integration_id),
    [integrations, syncForm.integration_id],
  );

  async function refresh() {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextIntegrations, nextIncidents, nextRecords, nextLinks, nextMockItems] = await Promise.all([
        getIntegrationHealthSummary(workspaceId),
        getIntegrations(workspaceId),
        getIncidents(workspaceId),
        getIntegrationSyncRecords({ workspace_id: workspaceId }),
        getExternalLinkedResources({ workspace_id: workspaceId }),
        getMockExternalItems(workspaceId),
      ]);
      setSummary(nextSummary);
      setIntegrations(nextIntegrations);
      setIncidents(nextIncidents);
      setRecords(nextRecords);
      setLinks(nextLinks);
      setMockItems(nextMockItems);
      setSyncForm((current) => ({
        incident_id: current.incident_id || nextIncidents[0]?.incident_id || "",
        integration_id: current.integration_id || nextIntegrations[0]?.integration_id || "",
      }));
    } catch (err) {
      setError(err.message || "Unable to load integrations.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [workspaceId]);

  function updateType(type) {
    setForm({ ...form, integration_type: type, config: defaultConfig(type) });
  }

  function updateConfig(key, value) {
    setForm({ ...form, config: { ...form.config, [key]: value } });
  }

  async function submitIntegration(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const created = await createIntegration({ ...form, workspace_id: workspaceId });
      setMessage(`Integration created: ${created.name}.`);
      setForm({ name: "Demo Jira Mock", integration_type: "jira", mode: "mock", enabled: true, config: defaultConfig("jira") });
      await refresh();
    } catch (err) {
      setError(err.message || "Unable to create integration.");
    }
  }

  async function runTest(integrationId) {
    const result = await testIntegration(integrationId);
    setMessage(result.result?.success ? "Integration test passed." : result.result?.error || "Integration test failed.");
    await refresh();
  }

  async function removeIntegration(integrationId) {
    if (!confirm("Delete this integration?")) return;
    await deleteIntegration(integrationId);
    setMessage("Integration deleted.");
    await refresh();
  }

  async function syncIncident() {
    const result = await syncIncidentToExternal(syncForm.integration_id, syncForm.incident_id);
    setSyncResult(result);
    setMessage(result.result?.success ? "Incident synced to external workflow." : result.result?.error || "Sync failed.");
    await refresh();
  }

  async function notifyIncident() {
    const result = await notifyIncidentExternal(syncForm.integration_id, syncForm.incident_id);
    setSyncResult(result);
    setMessage(result.result?.success ? "External notification sent." : result.result?.error || "Notification failed.");
    await refresh();
  }

  return (
    <section className="page integration-page">
      <div className="page-header">
        <div>
          <h2>External Workflow Integrations</h2>
          <p>Sync DriftGuard incidents with Jira-style tickets, GitHub Issues, Slack/Teams notifications, or generic webhooks. Mock mode works without API keys.</p>
        </div>
        <button className="secondary-button" onClick={refresh} disabled={loading}><RefreshCw size={16} />Refresh</button>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <div className="dashboard-grid">
        <Metric label="Total integrations" value={summary?.total_integrations || 0} />
        <Metric label="Enabled" value={summary?.enabled_integrations || 0} />
        <Metric label="Healthy" value={summary?.healthy_integrations || 0} />
        <Metric label="Errors" value={summary?.error_integrations || 0} />
      </div>
      <div className="dashboard-grid">
        <Metric label="Mock" value={summary?.mock_integrations || 0} />
        <Metric label="Live" value={summary?.live_integrations || 0} />
        <Metric label="Recent failures" value={summary?.recent_sync_failures || 0} />
        <Metric label="Mock items" value={mockItems.length} />
      </div>

      <div className="info-box">Mock mode requires no API keys and is recommended for demos.</div>

      <div className="incident-layout">
        {canManage && (
          <form className="panel incident-form" onSubmit={submitIntegration}>
            <div className="section-heading"><h3><PlugZap size={18} /> Create Integration</h3></div>
            <label>Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
            <div className="incident-form-row">
              <label>Integration type<select value={form.integration_type} onChange={(event) => updateType(event.target.value)}>{integrationTypes.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
              <label>Mode<select value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}><option>mock</option><option>live</option></select></label>
            </div>
            {Object.keys(form.config).map((key) => (
              <label key={key}>{key}<input value={form.config[key]} onChange={(event) => updateConfig(key, event.target.value)} type={key.includes("token") || key.includes("secret") ? "password" : "text"} /></label>
            ))}
            <label className="checkbox-label"><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} />Enabled</label>
            <button className="primary-button" type="submit"><Workflow size={16} />Create Integration</button>
          </form>
        )}

        <div className="panel">
          <div className="section-heading"><h3>Integration List</h3></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Type</th><th>Mode</th><th>Enabled</th><th>Health</th><th>Created</th><th>Actions</th></tr></thead>
              <tbody>
                {integrations.map((integration) => (
                  <tr key={integration.integration_id}>
                    <td><strong>{integration.name}</strong></td>
                    <td>{integration.integration_type}</td>
                    <td><Badge value={integration.mode} /></td>
                    <td>{integration.enabled ? "Yes" : "No"}</td>
                    <td><Badge value={integration.last_health_status} /></td>
                    <td>{formatDate(integration.created_at)}</td>
                    <td className="button-row">
                      {canManage && <button className="secondary-button" onClick={() => runTest(integration.integration_id)} type="button">Test</button>}
                      {canDelete && <button className="secondary-button danger" onClick={() => removeIntegration(integration.integration_id)} type="button"><Trash2 size={16} />Delete</button>}
                    </td>
                  </tr>
                ))}
                {integrations.length === 0 && <tr><td colSpan="7">No external integrations configured.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="section-heading"><h3><Send size={18} /> Incident Sync</h3></div>
        <div className="incident-filter-row">
          <select aria-label="Incident" value={syncForm.incident_id} onChange={(event) => setSyncForm({ ...syncForm, incident_id: event.target.value })}>
            <option value="">Select incident</option>
            {incidents.map((incident) => <option key={incident.incident_id} value={incident.incident_id}>{incident.title}</option>)}
          </select>
          <select aria-label="Integration" value={syncForm.integration_id} onChange={(event) => setSyncForm({ ...syncForm, integration_id: event.target.value })}>
            <option value="">Select integration</option>
            {integrations.map((integration) => <option key={integration.integration_id} value={integration.integration_id}>{integration.name}</option>)}
          </select>
        </div>
        <div className="button-row">
          {canManage && <button className="primary-button" disabled={!syncForm.incident_id || !syncForm.integration_id} onClick={syncIncident} type="button"><GitBranch size={16} />Sync Incident</button>}
          {canManage && <button className="secondary-button" disabled={!syncForm.incident_id || !syncForm.integration_id} onClick={notifyIncident} type="button"><Bell size={16} />Send Notification</button>}
        </div>
        {syncResult?.result && (
          <div className="info-box">
            External ID: {syncResult.result.external_id || "none"} | Status: {syncResult.result.external_status || "unknown"} | URL: {syncResult.result.external_url || "none"}
          </div>
        )}
        {selectedIntegration && <p className="empty-state">Selected integration: {selectedIntegration.integration_type} / {selectedIntegration.mode}</p>}
      </div>

      <div className="incident-automation-grid">
        <div className="panel">
          <div className="section-heading"><h3>Sync Records</h3></div>
          {records.map((record) => (
            <div className="agent-log-row" key={record.sync_record_id}>
              <span><Badge value={record.status} /> {record.action}</span>
              <small>{formatDate(record.created_at)}</small>
              <p>{record.integration_type} | {record.source_type} {record.source_id} | {record.external_id || record.error_message}</p>
            </div>
          ))}
          {records.length === 0 && <p className="empty-state">No sync records yet.</p>}
        </div>
        <div className="panel">
          <div className="section-heading"><h3><Link2 size={18} /> Linked Resources</h3></div>
          {links.map((link) => (
            <div className="agent-log-row" key={link.linked_resource_id}>
              <span>{link.external_type} {link.external_id}</span>
              <small>{link.source_type} {link.source_id}</small>
              <p>{link.external_url || "No URL"} | {link.external_status}</p>
            </div>
          ))}
          {links.length === 0 && <p className="empty-state">No linked resources yet.</p>}
        </div>
        <div className="panel">
          <div className="section-heading"><h3>Mock External Items</h3></div>
          {mockItems.map((item) => (
            <div className="agent-log-row" key={item.mock_id}>
              <span>{item.external_id} | {item.external_type}</span>
              <small>{formatDate(item.created_at)}</small>
              <p>{item.title} | {item.severity} | {item.status}</p>
            </div>
          ))}
          {mockItems.length === 0 && <p className="empty-state">No mock external items created.</p>}
        </div>
      </div>
    </section>
  );
}
