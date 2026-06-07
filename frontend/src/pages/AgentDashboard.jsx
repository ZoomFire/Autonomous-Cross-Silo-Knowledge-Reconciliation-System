import { useEffect, useMemo, useState } from "react";
import { Bot, Download, FileJson, Play, Route, Trash2 } from "lucide-react";
import {
  createAgentPlan,
  deleteAgentRun,
  exportAgentReportJson,
  exportAgentReportMarkdown,
  getAgentRun,
  getAgentRuns,
  getImportedSources,
  getRagChunks,
  runAgentWorkflow,
} from "../api.js";

const RUN_STATUS_CLASS = {
  completed: "success",
  partial: "warning",
  failed: "danger",
  running: "info",
  planned: "neutral",
};

const STEP_STATUS_CLASS = {
  completed: "success",
  failed: "danger",
  skipped: "neutral",
  running: "info",
  pending: "neutral",
};

const RISK_CLASS = {
  Critical: "danger",
  High: "orange",
  Medium: "warning",
  Low: "success",
  Unknown: "neutral",
};

function Badge({ value, kind = "neutral" }) {
  return <span className={`agent-badge ${kind}`}>{value || "Unknown"}</span>;
}

function formatDate(value) {
  if (!value) return "Not completed";
  return new Date(value).toLocaleString();
}

function outputSummary(step) {
  const summary = step.output?.summary || {};
  if (typeof summary === "string") return summary;
  const entries = Object.entries(summary).filter(([, value]) => value !== "" && value !== undefined && value !== null);
  if (!entries.length) return step.output?.message || "No output summary available.";
  return entries.map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`).join(" | ");
}

function ReportList({ items, emptyText }) {
  if (!items?.length) return <p className="muted">{emptyText}</p>;
  return (
    <ul className="agent-report-list">
      {items.map((item, index) => (
        <li key={`${item.case_id || item}-${index}`}>
          {typeof item === "string" ? item : `${item.case_id || "Item"} - ${item.title || item.root_cause_category || item.summary || "Details available"}`}
        </li>
      ))}
    </ul>
  );
}

export default function AgentDashboard({ user, workspaceId }) {
  const [goal, setGoal] = useState("Check payment module drift and prepare a full report.");
  const [plan, setPlan] = useState([]);
  const [runResult, setRunResult] = useState(null);
  const [runs, setRuns] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [useHybridReasoning, setUseHybridReasoning] = useState(false);
  const [hybridMode, setHybridMode] = useState("hybrid");
  const [hybridProvider, setHybridProvider] = useState("local");
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");

  const canRun = useMemo(() => ["admin", "engineer"].includes(user?.role), [user]);
  const finalReport = runResult?.final_report || runResult?.run?.final_report || {};

  async function loadHistory() {
    if (!workspaceId) return;
    const items = await getAgentRuns(workspaceId);
    setRuns(items);
  }

  async function loadWarnings() {
    if (!workspaceId) {
      setWarnings(["Workspace must be selected."]);
      return;
    }
    const nextWarnings = [];
    try {
      const [sources, chunks] = await Promise.all([getImportedSources(), getRagChunks()]);
      if (!sources.length) nextWarnings.push("No imported sources found. Please import sources using Connectors first.");
      if (!chunks.length) nextWarnings.push("Search index may be empty. Rebuild index from Search page for better results.");
    } catch {
      nextWarnings.push("Unable to check imported sources or search index status.");
    }
    setWarnings(nextWarnings);
  }

  useEffect(() => {
    setPlan([]);
    setRunResult(null);
    setError("");
    loadWarnings();
    loadHistory().catch((err) => setError(err.message));
  }, [workspaceId]);

  async function handlePlan() {
    setError("");
    setLoading("plan");
    try {
      const response = await createAgentPlan({ workspace_id: workspaceId, goal });
      setPlan(response.plan || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function handleRun() {
    setError("");
    setLoading("run");
    try {
      const response = await runAgentWorkflow({ workspace_id: workspaceId, goal, use_hybrid_reasoning: useHybridReasoning, reasoning_mode: hybridMode, provider: hybridProvider });
      setPlan(response.run?.plan || []);
      setRunResult(response);
      await loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function handleView(runId) {
    setError("");
    setLoading(runId);
    try {
      setRunResult(await getAgentRun(runId));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function handleDelete(runId) {
    setError("");
    setLoading(runId);
    try {
      await deleteAgentRun(runId);
      if (runResult?.run?.run_id === runId) setRunResult(null);
      await loadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  return (
    <section className="agent-page">
      <div className="page-heading">
        <div>
          <h2>Agentic Drift Investigation</h2>
          <p>Give DriftGuard AI a high-level investigation goal. The agent will plan and execute a multi-step workflow across search, evidence retrieval, dataset generation, evaluation, root cause analysis, timeline, impact graph, and final reporting.</p>
        </div>
        <Badge value="Level 3.4" kind="info" />
      </div>

      {warnings.map((warning) => <div className="warning-banner" key={warning}>{warning}</div>)}
      {error && <div className="error-banner">{error}</div>}

      <div className="agent-grid">
        <div className="panel-card agent-goal-card">
          <div className="panel-title">
            <Bot size={18} />
            <h3>Investigation Goal</h3>
          </div>
          <textarea
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="Example: Check payment module drift and prepare a full report."
            rows={5}
          />
          <div className="button-row">
            <button className="secondary-button" onClick={handlePlan} disabled={!workspaceId || !goal.trim() || loading === "plan"}>
              <Route size={16} />
              {loading === "plan" ? "Planning..." : "Generate Plan"}
            </button>
            <button className="primary-button" onClick={handleRun} disabled={!canRun || !workspaceId || !goal.trim() || loading === "run"}>
              <Play size={16} />
              {loading === "run" ? "Running..." : "Run Agent Workflow"}
            </button>
          </div>
          <label className="checkbox-label">
            <input type="checkbox" checked={useHybridReasoning} onChange={(event) => setUseHybridReasoning(event.target.checked)} />
            Use Hybrid Reasoning in Agent Workflow
          </label>
          {useHybridReasoning && (
            <div className="hybrid-controls">
              <label>Mode<select value={hybridMode} onChange={(event) => setHybridMode(event.target.value)}><option>local_only</option><option>llm_only</option><option>hybrid</option></select></label>
              <label>Provider<select value={hybridProvider} onChange={(event) => setHybridProvider(event.target.value)}><option>local</option><option>openai</option><option>gemini</option><option>ollama</option><option>custom</option></select></label>
            </div>
          )}
          {!canRun && <p className="muted">Viewer and reviewer roles can generate plans only.</p>}
        </div>

        <div className="panel-card">
          <div className="panel-title">
            <Route size={18} />
            <h3>Generated Plan</h3>
          </div>
          <div className="agent-timeline">
            {(plan.length ? plan : [{ step_name: "No plan generated yet.", tool_name: "agent_planner", status: "pending", step_index: 1 }]).map((step) => (
              <div className="agent-timeline-row" key={`${step.step_index}-${step.tool_name}`}>
                <span className="agent-step-number">{step.step_index}</span>
                <div>
                  <strong>{step.step_name}</strong>
                  <p>{step.tool_name}</p>
                </div>
                <Badge value={step.status} kind={STEP_STATUS_CLASS[step.status] || "neutral"} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {runResult && (
        <>
          <div className="panel-card agent-result-card">
            <div className="agent-result-header">
              <div>
                <h3>Agent Run Result</h3>
                <p>{runResult.run?.goal}</p>
              </div>
              <div className="agent-status-stack">
                <Badge value={runResult.run?.status} kind={RUN_STATUS_CLASS[runResult.run?.status] || "neutral"} />
                <Badge value={finalReport.risk_level} kind={RISK_CLASS[finalReport.risk_level] || "neutral"} />
              </div>
            </div>
            <div className="agent-metrics">
              <span>Created: {formatDate(runResult.run?.created_at)}</span>
              <span>Completed: {formatDate(runResult.run?.completed_at)}</span>
            </div>
            <div className="agent-summary-grid">
              <div>
                <h4>Executive Summary</h4>
                <p>{finalReport.executive_summary || "No executive summary available."}</p>
              </div>
              <div>
                <h4>Evidence Summary</h4>
                <p>{finalReport.evidence_summary || "No evidence summary available."}</p>
              </div>
              <div>
                <h4>Recommended Actions</h4>
                <ReportList items={finalReport.recommended_actions} emptyText="No actions generated." />
              </div>
            </div>
          </div>

          <div className="panel-card">
            <h3>Step Execution Logs</h3>
            <div className="agent-log-list">
              {runResult.steps?.map((step) => (
                <div className="agent-log-row" key={step.step_id}>
                  <div>
                    <strong>{step.step_name}</strong>
                    <span>{step.tool_name}</span>
                  </div>
                  <Badge value={step.status} kind={STEP_STATUS_CLASS[step.status] || "neutral"} />
                  <p>{outputSummary(step)}</p>
                  <small>{formatDate(step.started_at)} to {formatDate(step.completed_at)}</small>
                  {step.error_message && <p className="log-error">{step.error_message}</p>}
                </div>
              ))}
            </div>
          </div>

          <div className="panel-card">
            <h3>Final Agent Report</h3>
            <div className="agent-report-grid">
              <section><h4>Drift Findings</h4><ReportList items={finalReport.drift_findings} emptyText="No drift findings produced." /></section>
              <section><h4>Root Cause Findings</h4><ReportList items={finalReport.root_cause_findings} emptyText="No root cause findings produced." /></section>
              <section><h4>Timeline Summary</h4><ReportList items={finalReport.timeline_summary} emptyText="No timeline summary produced." /></section>
              <section><h4>Impact Summary</h4><ReportList items={finalReport.impact_summary} emptyText="No impact summary produced." /></section>
            </div>
          </div>
        </>
      )}

      <div className="panel-card">
        <h3>Agent Run History</h3>
        <div className="agent-history">
          {runs.map((run) => (
            <div className="agent-history-row" key={run.run_id}>
              <div>
                <strong>{run.run_id.slice(0, 8)}</strong>
                <p>{run.goal}</p>
                <small>{formatDate(run.created_at)} | {formatDate(run.completed_at)}</small>
              </div>
              <Badge value={run.status} kind={RUN_STATUS_CLASS[run.status] || "neutral"} />
              <Badge value={run.final_report?.risk_level || "Unknown"} kind={RISK_CLASS[run.final_report?.risk_level] || "neutral"} />
              <div className="history-actions">
                <button className="icon-button" onClick={() => handleView(run.run_id)} title="View run">View</button>
                <button className="icon-button" onClick={() => exportAgentReportJson(run.run_id)} title="Export JSON"><FileJson size={16} /></button>
                <button className="icon-button" onClick={() => exportAgentReportMarkdown(run.run_id)} title="Export Markdown"><Download size={16} /></button>
                {user?.role === "admin" && <button className="icon-button danger" onClick={() => handleDelete(run.run_id)} title="Delete run"><Trash2 size={16} /></button>}
              </div>
            </div>
          ))}
          {!runs.length && <p className="muted">No agent runs yet.</p>}
        </div>
      </div>
    </section>
  );
}
