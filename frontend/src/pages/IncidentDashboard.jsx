import { Bell, Download, MessageSquare, Plus, RefreshCw, Send, ShieldAlert, Trash2, UserPlus, Webhook } from "lucide-react";
import { useEffect, useState } from "react";
import {
  addIncidentComment,
  assignIncident,
  checkIncidentEscalations,
  createEscalationRule,
  createIncident,
  createIncidentWebhook,
  deleteIncident,
  exportIncidentMarkdown,
  getEscalationRules,
  getExternalLinkedResources,
  getIncident,
  getIncidentNotificationLogs,
  getIncidentSummary,
  getIncidentWebhooks,
  getIncidents,
  getIntegrations,
  notifyIncidentExternal,
  syncIncidentToExternal,
  testIncidentWebhook,
  updateIncidentStatus,
} from "../api.js";

const severities = ["Critical", "High", "Medium", "Low"];
const statuses = ["open", "triaged", "in_progress", "escalated", "resolved", "closed"];
const events = ["incident.created", "incident.status_changed", "incident.assigned", "incident.comment_added", "incident.escalated"];

function Badge({ value }) {
  const key = String(value || "none").toLowerCase();
  const tone = ["critical", "high", "medium", "low"].includes(key)
    ? key
    : ["resolved", "closed", "delivered"].includes(key)
      ? "success"
      : ["failed", "escalated"].includes(key)
        ? "failed"
        : ["open", "triaged", "in_progress"].includes(key)
          ? "warning"
          : "neutral";
  return <span className={`badge ${tone}`}>{value || "none"}</span>;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Not set";
}

function eventListToText(items) {
  return (items || []).join(", ");
}

function textToEventList(text) {
  return String(text || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function Metric({ label, value }) {
  return <div className="metric-card compact"><span>{label}</span><strong>{value ?? 0}</strong></div>;
}

export default function IncidentDashboard({ user, workspaceId }) {
  const [summary, setSummary] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [webhooks, setWebhooks] = useState([]);
  const [logs, setLogs] = useState([]);
  const [rules, setRules] = useState([]);
  const [externalIntegrations, setExternalIntegrations] = useState([]);
  const [externalLinks, setExternalLinks] = useState([]);
  const [externalIntegrationId, setExternalIntegrationId] = useState("");
  const [filters, setFilters] = useState({ status: "", severity: "" });
  const [incidentForm, setIncidentForm] = useState({ title: "Production drift review", description: "", severity: "High", source_type: "manual", assigned_to: "" });
  const [assignTo, setAssignTo] = useState("");
  const [commentText, setCommentText] = useState("");
  const [webhookForm, setWebhookForm] = useState({ name: "Incident webhook", url: "", event_types: eventListToText(["incident.created", "incident.escalated"]), enabled: true });
  const [ruleForm, setRuleForm] = useState({ name: "Critical open incident", severity: "Critical", status_filter: "open", escalate_after_minutes: 60, target_role: "admin", webhook_enabled: true });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canManage = ["admin", "engineer", "reviewer"].includes(user?.role);
  const canAutomate = ["admin", "engineer"].includes(user?.role);
  const canDelete = user?.role === "admin";

  async function refresh() {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const [nextSummary, nextIncidents, nextWebhooks, nextLogs, nextRules] = await Promise.all([
        getIncidentSummary(workspaceId),
        getIncidents(workspaceId, filters),
        getIncidentWebhooks(workspaceId),
        getIncidentNotificationLogs(workspaceId, 50),
        getEscalationRules(workspaceId),
      ]);
      const nextExternalIntegrations = canAutomate ? await getIntegrations(workspaceId) : [];
      setSummary(nextSummary);
      setIncidents(nextIncidents);
      setWebhooks(nextWebhooks);
      setLogs(nextLogs);
      setRules(nextRules);
      setExternalIntegrations(nextExternalIntegrations);
      setExternalIntegrationId((current) => current || nextExternalIntegrations[0]?.integration_id || "");
      if (selected?.incident?.incident_id) {
        setSelected(await getIncident(selected.incident.incident_id));
        setExternalLinks(await getExternalLinkedResources({ workspace_id: workspaceId, source_type: "incident", source_id: selected.incident.incident_id }));
      }
    } catch (err) {
      setError(err.message || "Unable to load incident data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [workspaceId, filters.status, filters.severity]);

  async function submitIncident(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const created = await createIncident({ ...incidentForm, workspace_id: workspaceId });
      setIncidentForm({ title: "Production drift review", description: "", severity: "High", source_type: "manual", assigned_to: "" });
      setMessage("Incident created.");
      await refresh();
      setSelected(await getIncident(created.incident_id));
    } catch (err) {
      setError(err.message || "Unable to create incident.");
    }
  }

  async function openIncident(incidentId) {
    setSelected(await getIncident(incidentId));
    setExternalLinks(await getExternalLinkedResources({ workspace_id: workspaceId, source_type: "incident", source_id: incidentId }));
    setAssignTo("");
    setCommentText("");
  }

  async function changeStatus(status) {
    if (!selected?.incident) return;
    const updated = await updateIncidentStatus(selected.incident.incident_id, status);
    setMessage(`Incident moved to ${updated.status}.`);
    await refresh();
    setSelected(await getIncident(updated.incident_id));
  }

  async function submitAssignment(event) {
    event.preventDefault();
    const updated = await assignIncident(selected.incident.incident_id, assignTo);
    setMessage("Assignment updated.");
    await refresh();
    setSelected(await getIncident(updated.incident_id));
  }

  async function submitComment(event) {
    event.preventDefault();
    await addIncidentComment(selected.incident.incident_id, commentText);
    setCommentText("");
    setMessage("Comment added.");
    setSelected(await getIncident(selected.incident.incident_id));
  }

  async function removeIncident(incidentId) {
    if (!confirm("Delete this incident?")) return;
    await deleteIncident(incidentId);
    setSelected(null);
    setMessage("Incident deleted.");
    await refresh();
  }

  async function submitWebhook(event) {
    event.preventDefault();
    await createIncidentWebhook({ ...webhookForm, workspace_id: workspaceId, event_types: textToEventList(webhookForm.event_types) });
    setWebhookForm({ name: "Incident webhook", url: "", event_types: eventListToText(["incident.created", "incident.escalated"]), enabled: true });
    setMessage("Webhook saved.");
    await refresh();
  }

  async function submitRule(event) {
    event.preventDefault();
    await createEscalationRule({ ...ruleForm, workspace_id: workspaceId, escalate_after_minutes: Number(ruleForm.escalate_after_minutes) });
    setRuleForm({ name: "Critical open incident", severity: "Critical", status_filter: "open", escalate_after_minutes: 60, target_role: "admin", webhook_enabled: true });
    setMessage("Escalation rule saved.");
    await refresh();
  }

  async function runEscalations() {
    const result = await checkIncidentEscalations(workspaceId);
    setMessage(`Escalation check complete: ${result.escalated_count} incident(s) escalated.`);
    await refresh();
  }

  async function syncSelectedIncident() {
    const result = await syncIncidentToExternal(externalIntegrationId, selected.incident.incident_id);
    setMessage(result.result?.success ? "Incident synced to external workflow." : result.result?.error || "External sync failed.");
    setExternalLinks(await getExternalLinkedResources({ workspace_id: workspaceId, source_type: "incident", source_id: selected.incident.incident_id }));
  }

  async function notifySelectedIncident() {
    const result = await notifyIncidentExternal(externalIntegrationId, selected.incident.incident_id);
    setMessage(result.result?.success ? "External notification sent." : result.result?.error || "External notification failed.");
    setExternalLinks(await getExternalLinkedResources({ workspace_id: workspaceId, source_type: "incident", source_id: selected.incident.incident_id }));
  }

  return (
    <section className="page incident-page">
      <div className="page-header">
        <div>
          <h2>Incident Management</h2>
          <p>Track drift incidents, owners, timeline events, escalation rules, and webhook deliveries.</p>
        </div>
        <button className="secondary-button" onClick={refresh} disabled={loading}><RefreshCw size={16} />Refresh</button>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <div className="dashboard-grid">
        <Metric label="Total Incidents" value={summary?.total || 0} />
        <Metric label="Open Work" value={summary?.open || 0} />
        <Metric label="Resolved" value={summary?.resolved || 0} />
        <Metric label="Closed" value={summary?.closed || 0} />
      </div>

      <div className="incident-layout">
        {canManage && (
          <form className="panel incident-form" onSubmit={submitIncident}>
            <div className="section-heading"><h3><ShieldAlert size={18} /> New Incident</h3></div>
            <label>Title<input value={incidentForm.title} onChange={(event) => setIncidentForm({ ...incidentForm, title: event.target.value })} required /></label>
            <label>Description<textarea value={incidentForm.description} onChange={(event) => setIncidentForm({ ...incidentForm, description: event.target.value })} /></label>
            <div className="incident-form-row">
              <label>Severity<select value={incidentForm.severity} onChange={(event) => setIncidentForm({ ...incidentForm, severity: event.target.value })}>{severities.map((severity) => <option key={severity}>{severity}</option>)}</select></label>
              <label>Source<select value={incidentForm.source_type} onChange={(event) => setIncidentForm({ ...incidentForm, source_type: event.target.value })}><option>manual</option><option>monitoring_alert</option><option>model_experiment</option><option>active_learning</option></select></label>
            </div>
            <label>Assign to<input value={incidentForm.assigned_to} onChange={(event) => setIncidentForm({ ...incidentForm, assigned_to: event.target.value })} placeholder="User ID or owner alias" /></label>
            <button className="primary-button" type="submit"><Plus size={16} />Create Incident</button>
          </form>
        )}

        <div className="panel">
          <div className="section-heading">
            <h3>Incident Queue</h3>
            <div className="incident-filter-row">
              <select aria-label="Status filter" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
                <option value="">All status</option>
                {statuses.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
              <select aria-label="Severity filter" value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}>
                <option value="">All severity</option>
                {severities.map((severity) => <option key={severity} value={severity}>{severity}</option>)}
              </select>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Title</th><th>Severity</th><th>Status</th><th>Owner</th><th>Updated</th><th>Action</th></tr></thead>
              <tbody>
                {incidents.map((incident) => (
                  <tr key={incident.incident_id}>
                    <td><strong>{incident.title}</strong><br /><span className="mono-cell">{incident.incident_id}</span></td>
                    <td><Badge value={incident.severity} /></td>
                    <td><Badge value={incident.status} /></td>
                    <td>{incident.assigned_to || "Unassigned"}</td>
                    <td>{formatDate(incident.updated_at)}</td>
                    <td><button className="secondary-button" onClick={() => openIncident(incident.incident_id)} type="button">Open</button></td>
                  </tr>
                ))}
                {incidents.length === 0 && <tr><td colSpan="6">No incidents match the current filters.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {selected?.incident && (
        <div className="incident-detail-grid">
          <div className="panel">
            <div className="section-heading">
              <h3>{selected.incident.title}</h3>
              <button className="secondary-button" onClick={() => exportIncidentMarkdown(selected.incident.incident_id)}><Download size={16} />Export</button>
            </div>
            <div className="report-grid">
              <div><span>Severity</span><strong><Badge value={selected.incident.severity} /></strong></div>
              <div><span>Status</span><strong><Badge value={selected.incident.status} /></strong></div>
              <div><span>SLA</span><strong>{formatDate(selected.incident.sla_due_at)}</strong></div>
            </div>
            <p className="report-summary">{selected.incident.description || "No description provided."}</p>
            {canManage && (
              <div className="button-row">
                {statuses.map((status) => <button key={status} className="secondary-button" onClick={() => changeStatus(status)} type="button">{status}</button>)}
                {canDelete && <button className="secondary-button danger" onClick={() => removeIncident(selected.incident.incident_id)} type="button"><Trash2 size={16} />Delete</button>}
              </div>
            )}
            {canManage && (
              <form className="incident-inline-form" onSubmit={submitAssignment}>
                <label>Assign<input value={assignTo} onChange={(event) => setAssignTo(event.target.value)} placeholder={selected.incident.assigned_to || "User ID or owner alias"} /></label>
                <button className="secondary-button" type="submit"><UserPlus size={16} />Assign</button>
              </form>
            )}
            {canManage && (
              <form className="incident-inline-form" onSubmit={submitComment}>
                <label>Comment<input value={commentText} onChange={(event) => setCommentText(event.target.value)} required /></label>
                <button className="secondary-button" type="submit"><MessageSquare size={16} />Add</button>
              </form>
            )}
            <div className="section-heading external-section-heading"><h3>External Integrations</h3></div>
            {canAutomate && (
              <div className="incident-inline-form">
                <label>Integration<select value={externalIntegrationId} onChange={(event) => setExternalIntegrationId(event.target.value)}>
                  <option value="">Select integration</option>
                  {externalIntegrations.map((integration) => <option key={integration.integration_id} value={integration.integration_id}>{integration.name}</option>)}
                </select></label>
                <div className="button-row">
                  <button className="secondary-button" disabled={!externalIntegrationId} onClick={syncSelectedIncident} type="button"><Send size={16} />Sync</button>
                  <button className="secondary-button" disabled={!externalIntegrationId} onClick={notifySelectedIncident} type="button"><Webhook size={16} />Notify</button>
                </div>
              </div>
            )}
            {externalLinks.map((link) => (
              <div className="agent-log-row" key={link.linked_resource_id}>
                <span>{link.external_type} {link.external_id}</span>
                <small>{link.external_status || "unknown"}</small>
                <p>{link.external_url || "No external URL"}</p>
              </div>
            ))}
            {externalLinks.length === 0 && <p className="empty-state">No linked external resources yet.</p>}
          </div>

          <div className="panel incident-activity">
            <div className="section-heading"><h3>Timeline</h3></div>
            {selected.timeline.map((event) => (
              <div className="agent-log-row" key={event.timeline_event_id}>
                <span>{event.event_type}</span>
                <small>{formatDate(event.created_at)}</small>
                <p>{event.message}</p>
              </div>
            ))}
            <div className="section-heading"><h3>Comments</h3></div>
            {selected.comments.map((comment) => (
              <div className="agent-log-row" key={comment.comment_id}>
                <span>{comment.user_id}</span>
                <small>{formatDate(comment.created_at)}</small>
                <p>{comment.comment_text}</p>
              </div>
            ))}
            {selected.comments.length === 0 && <p className="empty-state">No comments yet.</p>}
          </div>
        </div>
      )}

      <div className="incident-automation-grid">
        <div className="panel">
          <div className="section-heading"><h3><Webhook size={18} /> Webhooks</h3></div>
          {canAutomate && (
            <form className="incident-form compact" onSubmit={submitWebhook}>
              <label>Name<input value={webhookForm.name} onChange={(event) => setWebhookForm({ ...webhookForm, name: event.target.value })} required /></label>
              <label>URL<input value={webhookForm.url} onChange={(event) => setWebhookForm({ ...webhookForm, url: event.target.value })} placeholder="https://example.com/webhook" required /></label>
              <label>Events<input value={webhookForm.event_types} onChange={(event) => setWebhookForm({ ...webhookForm, event_types: event.target.value })} /></label>
              <label className="checkbox-label"><input type="checkbox" checked={webhookForm.enabled} onChange={(event) => setWebhookForm({ ...webhookForm, enabled: event.target.checked })} />Enabled</label>
              <button className="secondary-button" type="submit"><Send size={16} />Save Webhook</button>
            </form>
          )}
          {webhooks.map((webhook) => (
            <div className="agent-log-row" key={webhook.webhook_id}>
              <span>{webhook.name}</span>
              <small>{webhook.enabled ? "enabled" : "disabled"} | {eventListToText(webhook.event_types)}</small>
              <p className="mono-cell">{webhook.url}</p>
              {canAutomate && <button className="secondary-button" onClick={() => testIncidentWebhook(webhook.webhook_id, workspaceId)} type="button">Test</button>}
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="section-heading">
            <h3><Bell size={18} /> Escalation Rules</h3>
            {canAutomate && <button className="secondary-button" onClick={runEscalations} type="button">Check Now</button>}
          </div>
          {canAutomate && (
            <form className="incident-form compact" onSubmit={submitRule}>
              <label>Name<input value={ruleForm.name} onChange={(event) => setRuleForm({ ...ruleForm, name: event.target.value })} required /></label>
              <div className="incident-form-row">
                <label>Severity<select value={ruleForm.severity} onChange={(event) => setRuleForm({ ...ruleForm, severity: event.target.value })}>{severities.map((severity) => <option key={severity}>{severity}</option>)}</select></label>
                <label>Status<select value={ruleForm.status_filter} onChange={(event) => setRuleForm({ ...ruleForm, status_filter: event.target.value })}>{statuses.map((status) => <option key={status}>{status}</option>)}</select></label>
              </div>
              <div className="incident-form-row">
                <label>Minutes<input type="number" min="0" value={ruleForm.escalate_after_minutes} onChange={(event) => setRuleForm({ ...ruleForm, escalate_after_minutes: event.target.value })} /></label>
                <label>Target role<input value={ruleForm.target_role} onChange={(event) => setRuleForm({ ...ruleForm, target_role: event.target.value })} /></label>
              </div>
              <label className="checkbox-label"><input type="checkbox" checked={ruleForm.webhook_enabled} onChange={(event) => setRuleForm({ ...ruleForm, webhook_enabled: event.target.checked })} />Webhook enabled</label>
              <button className="secondary-button" type="submit"><Plus size={16} />Save Rule</button>
            </form>
          )}
          {rules.map((rule) => (
            <div className="agent-log-row" key={rule.rule_id}>
              <span>{rule.name}</span>
              <small>{rule.severity} | {rule.status_filter} | {rule.escalate_after_minutes} min</small>
              <p>Target: {rule.target_user_id || rule.target_role || "none"}</p>
            </div>
          ))}
        </div>

        <div className="panel">
          <div className="section-heading"><h3>Notification Logs</h3></div>
          {logs.map((log) => (
            <div className="agent-log-row" key={log.delivery_id}>
              <span><Badge value={log.status} /> {log.event_type}</span>
              <small>{formatDate(log.created_at)}</small>
              <p>{log.error_message || log.response_text || `HTTP ${log.response_status_code || "n/a"}`}</p>
            </div>
          ))}
          {logs.length === 0 && <p className="empty-state">No webhook delivery attempts recorded.</p>}
        </div>
      </div>
    </section>
  );
}
