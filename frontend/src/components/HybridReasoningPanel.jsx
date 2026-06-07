import { useState } from "react";
import { Brain, Play } from "lucide-react";
import { runHybridReasoning } from "../api.js";

const MODE_CLASS = {
  local_only: "info",
  llm_only: "purple",
  hybrid: "success",
};

function Badge({ value, kind = "neutral" }) {
  return <span className={`agent-badge ${kind}`}>{value}</span>;
}

function JsonBlock({ title, value }) {
  return (
    <div className="hybrid-json-block">
      <h4>{title}</h4>
      <pre className="json-preview">{JSON.stringify(value || {}, null, 2)}</pre>
    </div>
  );
}

export default function HybridReasoningPanel({ taskType, inputContext, onResult, workspaceId }) {
  const [reasoningMode, setReasoningMode] = useState("local_only");
  const [provider, setProvider] = useState("local");
  const [runtimeApiKey, setRuntimeApiKey] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleRun() {
    setLoading(true);
    setError("");
    try {
      const response = await runHybridReasoning({
        workspace_id: workspaceId,
        task_type: taskType,
        reasoning_mode: reasoningMode,
        provider,
        runtime_api_key: runtimeApiKey,
        input_context: inputContext,
      });
      setResult(response);
      onResult?.(response);
    } catch (err) {
      setError(err.message || "Hybrid reasoning failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel-card hybrid-panel">
      <div className="panel-title">
        <Brain size={18} />
        <h3>Hybrid Reasoning Options</h3>
        <Badge value={reasoningMode} kind={MODE_CLASS[reasoningMode]} />
      </div>
      <div className="hybrid-controls">
        <label>Reasoning mode
          <select value={reasoningMode} onChange={(event) => setReasoningMode(event.target.value)}>
            <option value="local_only">local_only</option>
            <option value="llm_only">llm_only</option>
            <option value="hybrid">hybrid</option>
          </select>
        </label>
        <label>Provider
          <select value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option value="local">local</option>
            <option value="openai">openai</option>
            <option value="gemini">gemini</option>
            <option value="ollama">ollama</option>
            <option value="custom">custom</option>
          </select>
        </label>
        <label>Runtime API key
          <input value={runtimeApiKey} onChange={(event) => setRuntimeApiKey(event.target.value)} placeholder="Optional, not stored as plaintext" type="password" />
        </label>
        <button className="secondary-button" onClick={handleRun} disabled={loading || !workspaceId}>
          <Play size={16} />
          {loading ? "Running..." : "Run Hybrid Reasoning"}
        </button>
      </div>
      <p className="muted">Local-only mode requires no API key. External providers are optional and fail back safely when unavailable.</p>
      {error && <div className="error-banner">{error}</div>}
      {result && (
        <div className="hybrid-result-grid">
          <div className="badge-row">
            <Badge value={result.validation?.valid ? "valid" : "invalid"} kind={result.validation?.valid ? "success" : "danger"} />
            <Badge value={result.provider} kind="neutral" />
            <Badge value={result.status} kind={result.status === "failed" ? "danger" : "success"} />
          </div>
          {!!result.validation?.warnings?.length && <div className="warning-banner">{result.validation.warnings.join(" ")}</div>}
          <JsonBlock title="Local Output" value={result.local_output} />
          <JsonBlock title="LLM Output" value={result.llm_output} />
          <JsonBlock title="Comparison" value={result.comparison} />
          <JsonBlock title="Final Output" value={result.final_output} />
        </div>
      )}
    </div>
  );
}

