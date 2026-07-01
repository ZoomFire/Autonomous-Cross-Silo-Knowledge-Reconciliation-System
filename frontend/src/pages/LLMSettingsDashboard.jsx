import { useEffect, useMemo, useState } from "react";
import { Brain, Check, Download, Edit3, RefreshCw, Save, Trash2, X } from "lucide-react";
import {
  createPromptTemplate,
  deletePromptTemplate,
  exportReasoningTraceMarkdown,
  getHybridResults,
  getPromptTemplates,
  getReasoningTrace,
  getReasoningTraces,
  getLLMSettings,
  saveLLMSettings,
  updateHybridApproval,
  updateLLMSettings,
  updatePromptTemplate,
} from "../api.js";

const PROVIDERS = ["local", "openai", "gemini", "grok", "ollama", "custom"];
const TASK_TYPES = ["claim_extraction", "contradiction_detection", "root_cause_analysis", "fix_recommendation", "rag_answer", "agent_report", "severity_classification", "drift_type_classification"];

function Badge({ value, kind = "neutral" }) {
  return <span className={`agent-badge ${kind}`}>{value || "Unknown"}</span>;
}

function shortId(value) {
  return value ? value.slice(0, 8) : "";
}

function formatLabel(value) {
  return String(value || "").replace(/_/g, " ");
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Not saved yet";
}

export default function LLMSettingsDashboard({ user, workspaceId }) {
  const [settings, setSettings] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [traces, setTraces] = useState([]);
  const [hybridResults, setHybridResults] = useState([]);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [settingsForm, setSettingsForm] = useState({ provider: "local", model_name: "local-rule-engine", reasoning_mode: "local_only", runtime_api_key: "", enabled: true, config: {} });
  const [templateForm, setTemplateForm] = useState({ template_id: "", name: "", task_type: "contradiction_detection", template_text: "" });

  const canManage = useMemo(() => ["admin", "engineer"].includes(user?.role), [user]);
  const activeSettings = useMemo(() => {
    const byProvider = new Map();
    settings.forEach((item) => {
      if (!byProvider.has(item.provider)) byProvider.set(item.provider, item);
    });
    return Array.from(byProvider.values());
  }, [settings]);
  const isEditingTemplate = templateForm.template_id && !templateForm.template_id.startsWith("default-");

  async function loadAll() {
    if (!workspaceId) return;
    setError("");
    try {
      const [traceItems, resultItems] = await Promise.all([getReasoningTraces(workspaceId), getHybridResults(workspaceId)]);
      setTraces(traceItems);
      setHybridResults(resultItems);
      if (canManage) {
        const [settingsItems, templateItems] = await Promise.all([getLLMSettings(workspaceId), getPromptTemplates(workspaceId)]);
        setSettings(settingsItems);
        setTemplates(templateItems);
        if (settingsItems[0]) {
          setSettingsForm({ ...settingsItems[0], runtime_api_key: "" });
        }
      }
    } catch (err) {
      setError(err.message || "Unable to load AI settings.");
    }
  }

  useEffect(() => {
    loadAll();
  }, [workspaceId, canManage]);

  async function saveSettings() {
    setBusy("settings");
    setError("");
    try {
      if (settingsForm.settings_id) {
        await updateLLMSettings(settingsForm.settings_id, settingsForm);
      } else {
        await saveLLMSettings({ ...settingsForm, workspace_id: workspaceId });
      }
      setMessage("LLM settings saved.");
      await loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function saveTemplate() {
    setBusy("template");
    setError("");
    try {
      if (templateForm.template_id && !templateForm.template_id.startsWith("default-")) {
        await updatePromptTemplate(templateForm.template_id, templateForm);
      } else {
        await createPromptTemplate({ ...templateForm, workspace_id: workspaceId });
      }
      setTemplateForm({ template_id: "", name: "", task_type: "contradiction_detection", template_text: "" });
      setMessage("Prompt template saved.");
      await loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function removeTemplate(templateId) {
    setBusy(templateId);
    try {
      await deletePromptTemplate(templateId);
      await loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function viewTrace(traceId) {
    setBusy(traceId);
    try {
      setSelectedTrace(await getReasoningTrace(traceId));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function approveResult(resultId, approvalStatus) {
    setBusy(resultId);
    try {
      await updateHybridApproval(resultId, { approval_status: approvalStatus, approved_by_user: approvalStatus === "approved" });
      setMessage(approvalStatus === "approved" ? "Hybrid result approved." : "Hybrid result rejected.");
      await loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="agent-page">
      <div className="page-heading">
        <div>
          <h2>Hybrid Intelligence Settings</h2>
          <p>Configure local or optional LLM-based reasoning. DriftGuard AI works without API keys using the local rule-based engine.</p>
        </div>
        <Badge value="Level 3.4" kind="info" />
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}
      {!canManage && <div className="warning-banner">Reviewer access is read-only for traces and hybrid results.</div>}

      {canManage && (
        <div className="agent-grid hybrid-settings-grid">
          <div className="panel-card hybrid-settings-panel">
            <div className="panel-title"><Brain size={18} /><h3>Reasoning Mode</h3></div>
            <div className="hybrid-settings-form">
              <label>Provider<select value={settingsForm.provider} onChange={(event) => setSettingsForm({ ...settingsForm, provider: event.target.value })}>{PROVIDERS.map((provider) => <option key={provider}>{provider}</option>)}</select></label>
              <label>Model name<input value={settingsForm.model_name} onChange={(event) => setSettingsForm({ ...settingsForm, model_name: event.target.value })} /></label>
              <label>Reasoning mode<select value={settingsForm.reasoning_mode} onChange={(event) => setSettingsForm({ ...settingsForm, reasoning_mode: event.target.value })}><option>local_only</option><option>llm_only</option><option>hybrid</option></select></label>
              <label className="hybrid-key-field">Runtime API key<input type="password" value={settingsForm.runtime_api_key || ""} onChange={(event) => setSettingsForm({ ...settingsForm, runtime_api_key: event.target.value })} placeholder="Optional, not stored as plaintext" /></label>
              <label className="checkbox-label hybrid-enabled"><input type="checkbox" checked={settingsForm.enabled} onChange={(event) => setSettingsForm({ ...settingsForm, enabled: event.target.checked })} /> Enabled</label>
            </div>
            <div className="warning-banner">External provider support is optional. Local-only mode requires no API key.</div>
            <button className="primary-button" onClick={saveSettings} disabled={busy === "settings" || !workspaceId}><Save size={16} />Save Settings</button>
          </div>

          <div className="panel-card">
            <h3>Saved Settings</h3>
            <div className="settings-list">
              {activeSettings.map((item) => (
                <button className="settings-row" key={item.settings_id} type="button" onClick={() => setSettingsForm({ ...item, runtime_api_key: "" })}>
                  <span>
                    <strong>{item.provider}</strong>
                    <small>{item.model_name}{item.api_key_masked ? ` | key ${item.api_key_masked}` : ""}</small>
                  </span>
                  <Badge value={formatLabel(item.reasoning_mode)} kind="info" />
                </button>
              ))}
              {!activeSettings.length && <p className="muted">No settings saved yet.</p>}
            </div>
          </div>
        </div>
      )}

      {canManage && (
        <div className="panel-card prompt-template-panel">
          <div className="section-heading">
            <h3>Prompt Template Manager</h3>
            {templateForm.template_id && <button className="secondary-button" type="button" onClick={() => setTemplateForm({ template_id: "", name: "", task_type: "contradiction_detection", template_text: "" })}>Clear Edit</button>}
          </div>
          <div className="template-form-grid">
            <label>Template name<input value={templateForm.name} onChange={(event) => setTemplateForm({ ...templateForm, name: event.target.value })} /></label>
            <label>Task type<select value={templateForm.task_type} onChange={(event) => setTemplateForm({ ...templateForm, task_type: event.target.value })}>{TASK_TYPES.map((item) => <option key={item}>{item}</option>)}</select></label>
            <button className="secondary-button" onClick={saveTemplate} disabled={busy === "template" || !templateForm.name || !templateForm.template_text}><Save size={16} />{isEditingTemplate ? "Update Template" : "Save Template"}</button>
          </div>
          <textarea className="template-editor" value={templateForm.template_text} onChange={(event) => setTemplateForm({ ...templateForm, template_text: event.target.value })} placeholder="Template text with {variables}" rows={7} />
          <div className="template-list">
            {templates.map((template) => (
              <div className="template-row" key={template.template_id}>
                <div><strong>{template.name}</strong><p>{formatLabel(template.task_type)}</p><small>{template.created_at ? formatDate(template.created_at) : "Default template"}</small></div>
                <Badge value={template.template_id.startsWith("default-") ? "default" : "custom"} kind="neutral" />
                <div className="history-actions">
                  <button className="icon-button" onClick={() => setTemplateForm(template)} title="Edit prompt template"><Edit3 size={16} /></button>
                  {!template.template_id.startsWith("default-") && <button className="icon-button danger" onClick={() => removeTemplate(template.template_id)} title="Delete prompt template" disabled={busy === template.template_id}><Trash2 size={16} /></button>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="agent-grid hybrid-review-grid">
        <div className="panel-card">
          <div className="section-heading"><h3>Reasoning Trace History</h3><button className="secondary-button" onClick={loadAll}><RefreshCw size={16} />Refresh</button></div>
          <div className="hybrid-card-list">
            {traces.map((trace) => (
              <div className="hybrid-review-row" key={trace.trace_id}>
                <div className="hybrid-row-main"><strong>{shortId(trace.trace_id)}</strong><p>{formatLabel(trace.task_type)}</p><small>{formatDate(trace.created_at)}</small></div>
                <div className="hybrid-row-badges">
                <Badge value={formatLabel(trace.reasoning_mode)} kind="info" />
                <Badge value={trace.status} kind={trace.status === "failed" ? "danger" : "success"} />
                </div>
                <div className="history-actions">
                  <button className="icon-button" onClick={() => viewTrace(trace.trace_id)} title="View reasoning trace">View</button>
                  <button className="icon-button" onClick={() => exportReasoningTraceMarkdown(trace.trace_id)} title="Download trace markdown"><Download size={16} /></button>
                </div>
              </div>
            ))}
            {!traces.length && <p className="muted">No reasoning traces yet.</p>}
          </div>
        </div>

        <div className="panel-card">
          <h3>Hybrid Results Review</h3>
          <div className="hybrid-card-list">
            {hybridResults.map((item) => (
              <div className="hybrid-review-row" key={item.result_id}>
                <div className="hybrid-row-main"><strong>{shortId(item.result_id)}</strong><p>{formatLabel(item.task_type)}</p><small>{formatDate(item.created_at)}</small></div>
                <div className="hybrid-row-badges">
                <Badge value={item.approval_status} kind={item.approval_status === "approved" ? "success" : item.approval_status === "rejected" ? "danger" : "warning"} />
                <Badge value={item.comparison?.agreement ? "agreement" : "difference"} kind={item.comparison?.agreement ? "success" : "warning"} />
                </div>
                <div className="history-actions">
                  <button className="icon-button" onClick={() => setSelectedTrace({ final_output: item.final_result, validation_result: item.comparison, trace_id: item.trace_id })} title="View hybrid result">View</button>
                  <button className="icon-button" onClick={() => approveResult(item.result_id, "approved")} title="Approve hybrid result" disabled={busy === item.result_id}><Check size={16} /></button>
                  <button className="icon-button danger" onClick={() => approveResult(item.result_id, "rejected")} title="Reject hybrid result" disabled={busy === item.result_id}><X size={16} /></button>
                </div>
              </div>
            ))}
            {!hybridResults.length && <p className="muted">No hybrid results yet.</p>}
          </div>
        </div>
      </div>

      {selectedTrace && (
        <div className="panel-card">
          <h3>Trace Detail</h3>
          <pre className="json-preview">{JSON.stringify(selectedTrace, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}

