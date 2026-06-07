import { useState } from "react";
import { Activity, RotateCcw, Trash2 } from "lucide-react";
import { analyzeDrift, predictWithMLModel } from "../api.js";
import InputPanel from "./InputPanel.jsx";
import DashboardCards from "./DashboardCards.jsx";
import TruthTriangle from "./TruthTriangle.jsx";
import ClaimTable from "./ClaimTable.jsx";
import DriftReport from "./DriftReport.jsx";
import HybridReasoningPanel from "./HybridReasoningPanel.jsx";

const emptyForm = {
  documentation: "",
  code: "",
  jira: "",
  commit: "",
  logs: "",
  database_config: "",
};

const sampleForm = {
  documentation: "The /api/payment/refund endpoint is public and can be accessed by customers without special internal permissions.",
  code: '@internal_only\n@app.route("/api/payment/refund")\ndef refund_payment():\n    return process_refund()',
  jira: "JIRA-231: Customer refund feature is completed and ready for production.",
  commit: "Added internal-only access to refund API for security compliance.",
  logs: "403 Forbidden: customer_123 tried to access /api/payment/refund",
  database_config: "access_type=internal, feature_enabled=true",
};

export default function ManualAnalysis({ workspaceId }) {
  const [form, setForm] = useState(emptyForm);
  const [result, setResult] = useState(null);
  const [mlPrediction, setMlPrediction] = useState(null);
  const [useDeployedMl, setUseDeployedMl] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAnalyze() {
    setLoading(true);
    setError("");
    try {
      const response = await analyzeDrift(form);
      setResult(response);
      setMlPrediction(null);
      if (useDeployedMl && workspaceId) {
        setMlPrediction(await predictWithMLModel({ workspace_id: workspaceId, task_type: "label_classification", input_context: form }));
      }
    } catch {
      setError("Analysis failed. Please check backend server.");
    } finally {
      setLoading(false);
    }
  }

  function clearAll() {
    setForm(emptyForm);
    setResult(null);
    setMlPrediction(null);
    setError("");
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h2>Manual Drift Analysis</h2>
          <p>Paste enterprise data from docs, code, Jira, commits, logs, and database config.</p>
        </div>
        <div className="header-actions">
          <button className="secondary-button" onClick={() => setForm(sampleForm)}>
            <RotateCcw size={17} />
            Load Sample
          </button>
          <button className="secondary-button" onClick={clearAll}>
            <Trash2 size={17} />
            Clear
          </button>
          <button className="primary-button" onClick={handleAnalyze} disabled={loading}>
            <Activity size={17} />
            {loading ? "Analyzing..." : "Analyze Drift"}
          </button>
        </div>
      </div>

      <HybridReasoningPanel taskType="contradiction_detection" inputContext={form} workspaceId={workspaceId} />
      <label className="checkbox-label">
        <input type="checkbox" checked={useDeployedMl} onChange={(event) => setUseDeployedMl(event.target.checked)} />
        Use deployed ML model if available
      </label>
      <InputPanel form={form} onChange={setForm} />
      {error && <div className="error-banner">{error}</div>}
      {mlPrediction && (
        <div className={mlPrediction.fallback_used ? "warning-banner" : "success-banner"}>
          ML prediction: {mlPrediction.prediction || "fallback required"} | Model: {mlPrediction.model_type || "rule_based"} | Fallback used: {mlPrediction.fallback_used ? "yes" : "no"}
        </div>
      )}

      {result && (
        <div className="results-stack">
          <DashboardCards claims={result.claims} report={result.drift_report} />
          <DriftReport report={result.drift_report} />
          <TruthTriangle triangle={result.truth_triangle} />
          <ClaimTable claims={result.claims} />
        </div>
      )}
    </section>
  );
}
