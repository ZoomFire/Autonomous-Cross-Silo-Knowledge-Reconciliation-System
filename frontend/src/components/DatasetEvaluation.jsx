import { useEffect, useMemo, useState } from "react";
import { Database, Download, FileJson, PlayCircle, Upload } from "lucide-react";
import {
  exportLatestEvaluationJson,
  exportLatestEvaluationMarkdown,
  compareEvaluations,
  buildTrainingDataset,
  deleteEvaluationResult,
  deleteFeedback,
  deleteSavedDataset,
  evaluateSavedDataset,
  exportCorrectedDataset,
  getDatasetLibrary,
  getAllFeedback,
  getEvaluationHistory,
  getEvaluationResult,
  getFeedbackForEvaluation,
  getFeedbackSummaryForEvaluation,
  getLatestRootCauseReport,
  getLatestImpactGraph,
  getLatestTimeline,
  getImpactGraphForEvaluation,
  getRootCauseReportForEvaluation,
  getTimelineForEvaluation,
  getSampleDataset,
  getSavedDataset,
  runDatasetEvaluation,
  saveUploadedDataset,
  saveCaseFeedback,
  uploadDatasetEvaluate,
  uploadDatasetPreview,
} from "../api.js";
import RootCauseDashboard from "./RootCauseDashboard.jsx";
import TimelineDashboard from "./TimelineDashboard.jsx";
import ImpactGraphDashboard from "./ImpactGraphDashboard.jsx";
import HybridReasoningPanel from "./HybridReasoningPanel.jsx";
import PermissionGuard, { hasPermission } from "./PermissionGuard.jsx";

const datasetTemplate = [
  {
    case_id: "REAL-001",
    title: "Public docs but internal code",
    documentation: "The /api/payment/refund endpoint is public.",
    code: "@internal_only\n@app.route('/api/payment/refund')\ndef refund_payment():\n    return process_refund()",
    jira: "Refund feature is customer-facing and ready for production.",
    commit: "Added internal-only access for security compliance.",
    logs: "403 Forbidden: customer tried to access /api/payment/refund",
    database_config: "access_type=internal, feature_enabled=true",
    expected_label: "contradiction",
    expected_drift_type: "Documentation Drift",
    expected_severity: "Critical",
  },
];

function percent(value) {
  return `${value ?? 0}%`;
}

function objectEntries(value = {}) {
  return Object.entries(value);
}

function EvaluationCards({ evaluation }) {
  const cards = [
    ["Total Cases", evaluation.total_cases],
    ["Correct", evaluation.correct_cases ?? evaluation.passed],
    ["Incorrect", evaluation.incorrect_cases ?? evaluation.failed],
    ["Accuracy", percent(evaluation.accuracy)],
    ["Contradiction Cases", evaluation.contradiction_cases],
    ["No Drift Cases", evaluation.no_drift_cases],
    ["Manual Review Cases", evaluation.manual_review_cases],
  ];

  return (
    <div className="evaluation-grid">
      {cards.map(([label, value]) => (
        <div className="metric-card compact" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function DatasetTable({ cases, sourceLabel }) {
  if (cases.length === 0) return null;

  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Dataset Preview</h3>
        {sourceLabel && <span className="source-badge">{sourceLabel}</span>}
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Title</th>
              <th>Expected Label</th>
              <th>Expected Drift Type</th>
              <th>Expected Severity</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((datasetCase) => (
              <tr key={datasetCase.case_id}>
                <td>{datasetCase.case_id}</td>
                <td>{datasetCase.title}</td>
                <td>{datasetCase.expected_label}</td>
                <td>{datasetCase.expected_drift_type}</td>
                <td><span className={`badge ${datasetCase.expected_severity.toLowerCase()}`}>{datasetCase.expected_severity}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function DistributionList({ title, distribution }) {
  return (
    <div className="distribution-box">
      <span>{title}</span>
      {objectEntries(distribution).map(([key, value]) => (
        <div key={key}>
          <strong>{key}</strong>
          <em>{value}</em>
        </div>
      ))}
    </div>
  );
}

function DatasetQualityCard({ report }) {
  if (!report) return null;

  return (
    <section className="panel">
      <div className="section-heading">
        <h3>Dataset Quality</h3>
        <span className={report.quality_score >= 80 ? "badge passed" : "badge warning"}>{report.quality_score}/100</span>
      </div>
      <div className="quality-grid">
        <div className="quality-stat"><span>Total Cases</span><strong>{report.total_cases}</strong></div>
        <div className="quality-stat"><span>Valid Cases</span><strong>{report.valid_cases}</strong></div>
        <div className="quality-stat"><span>Invalid Cases</span><strong>{report.invalid_cases}</strong></div>
      </div>
      <div className="distribution-grid">
        <DistributionList title="Label Distribution" distribution={report.label_distribution} />
        <DistributionList title="Drift Type Distribution" distribution={report.drift_type_distribution} />
        <DistributionList title="Severity Distribution" distribution={report.severity_distribution} />
      </div>
      {(report.empty_field_warnings?.length > 0 || report.missing_field_warnings?.length > 0) && (
        <div className="warning-box">
          {[...(report.missing_field_warnings || []), ...(report.empty_field_warnings || [])].slice(0, 8).map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      )}
    </section>
  );
}

function AccuracyBreakdown({ evaluation }) {
  const cards = [
    ["Overall Accuracy", percent(evaluation.accuracy)],
    ["Label Accuracy", percent(evaluation.label_accuracy)],
    ["Drift Type Accuracy", percent(evaluation.drift_type_accuracy)],
    ["Severity Accuracy", percent(evaluation.severity_accuracy)],
  ];

  return (
    <div className="dashboard-grid">
      {cards.map(([label, value]) => (
        <div className="metric-card compact" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function MatrixTable({ title, matrix }) {
  const columns = Array.from(new Set(objectEntries(matrix).flatMap(([, row]) => Object.keys(row)))).sort();
  if (!matrix || columns.length === 0) return null;

  return (
    <section className="panel">
      <div className="section-heading"><h3>{title}</h3></div>
      <div className="table-wrap">
        <table className="matrix-table">
          <thead>
            <tr>
              <th>Expected</th>
              {columns.map((column) => <th key={column}>{column}</th>)}
            </tr>
          </thead>
          <tbody>
            {objectEntries(matrix).map(([expected, row]) => (
              <tr key={expected}>
                <td><strong>{expected}</strong></td>
                {columns.map((column) => <td key={column}>{row[column] || 0}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Filters({ filters, setFilters, results }) {
  const labels = Array.from(new Set(results.flatMap((result) => [result.expected_label, result.predicted_label]))).filter(Boolean);
  const driftTypes = Array.from(new Set(results.flatMap((result) => [result.expected_drift_type, result.predicted_drift_type]))).filter(Boolean);
  const severities = Array.from(new Set(results.flatMap((result) => [result.expected_severity, result.predicted_severity]))).filter(Boolean);

  function update(key, value) {
    setFilters({ ...filters, [key]: value });
  }

  return (
    <section className="panel filters-panel">
      <div className="section-heading"><h3>Filters</h3></div>
      <div className="filters-grid">
        <label>
          Result
          <select value={filters.correctness} onChange={(event) => update("correctness", event.target.value)}>
            <option value="all">Show all</option>
            <option value="correct">Correct only</option>
            <option value="incorrect">Incorrect only</option>
          </select>
        </label>
        <label>
          Severity
          <select value={filters.severity} onChange={(event) => update("severity", event.target.value)}>
            <option value="all">All severities</option>
            {severities.map((severity) => <option key={severity} value={severity}>{severity}</option>)}
          </select>
        </label>
        <label>
          Drift Type
          <select value={filters.driftType} onChange={(event) => update("driftType", event.target.value)}>
            <option value="all">All drift types</option>
            {driftTypes.map((driftType) => <option key={driftType} value={driftType}>{driftType}</option>)}
          </select>
        </label>
        <label>
          Label
          <select value={filters.label} onChange={(event) => update("label", event.target.value)}>
            <option value="all">All labels</option>
            {labels.map((label) => <option key={label} value={label}>{label}</option>)}
          </select>
        </label>
      </div>
    </section>
  );
}

const labelOptions = ["contradiction", "no_contradiction", "uncertain"];
const driftTypeOptions = ["Documentation Drift", "Code Drift", "Ticket Drift", "Configuration Drift", "Runtime Drift", "No Drift", "Unknown"];
const severityOptions = ["Critical", "High", "Medium", "Low", "None"];

function ResultDetails({ result, humanReviewMode, feedback, onSaveFeedback, activeEvaluationId }) {
  const correct = result.overall_correct ?? result.passed;
  const [form, setForm] = useState({
    corrected_label: feedback?.corrected_label || result.expected_label,
    corrected_drift_type: feedback?.corrected_drift_type || result.expected_drift_type,
    corrected_severity: feedback?.corrected_severity || result.expected_severity,
    review_status: feedback?.review_status || "unreviewed",
    reviewer_notes: feedback?.reviewer_notes || "",
    correction_reason: feedback?.correction_reason || "",
  });

  useEffect(() => {
    setForm({
      corrected_label: feedback?.corrected_label || result.expected_label,
      corrected_drift_type: feedback?.corrected_drift_type || result.expected_drift_type,
      corrected_severity: feedback?.corrected_severity || result.expected_severity,
      review_status: feedback?.review_status || "unreviewed",
      reviewer_notes: feedback?.reviewer_notes || "",
      correction_reason: feedback?.correction_reason || "",
    });
  }, [feedback, result]);

  function update(key, value) {
    setForm({ ...form, [key]: value });
  }

  return (
    <div className={correct ? "case-detail correct" : "case-detail mismatch"}>
      <div className="case-detail-header">
        <strong>{result.case_id} - {result.title}</strong>
        <div className="badge-row">
          <span className={correct ? "badge passed" : "badge failed"}>{correct ? "Correct" : "Mismatch"}</span>
          <span className={feedback?.review_status === "reviewed" ? "badge passed" : "badge neutral"}>{feedback?.review_status === "reviewed" ? "Reviewed" : "Unreviewed"}</span>
          {feedback && <span className="badge info-badge">Correction Saved</span>}
        </div>
      </div>
      <div className="comparison-grid">
        <div>
          <span>Expected</span>
          <p>{result.expected_label} / {result.expected_drift_type} / {result.expected_severity}</p>
        </div>
        <div>
          <span>Predicted</span>
          <p>{result.predicted_label} / {result.predicted_drift_type} / {result.predicted_severity}</p>
        </div>
      </div>
      {!correct && <p className="mismatch-reason">{result.mismatch_reason}</p>}
      <p>{result.explanation}</p>
      <p><strong>Evidence sources:</strong> {(result.evidence_sources || []).join(", ") || "None"}</p>
      {humanReviewMode && (
        <div className="feedback-form">
          <label>Corrected Label<select value={form.corrected_label} onChange={(event) => update("corrected_label", event.target.value)}>{labelOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Corrected Drift Type<select value={form.corrected_drift_type} onChange={(event) => update("corrected_drift_type", event.target.value)}>{driftTypeOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Corrected Severity<select value={form.corrected_severity} onChange={(event) => update("corrected_severity", event.target.value)}>{severityOptions.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Review Status<select value={form.review_status} onChange={(event) => update("review_status", event.target.value)}><option>reviewed</option><option>unreviewed</option></select></label>
          <label className="wide-field">Reviewer Notes<textarea value={form.reviewer_notes} onChange={(event) => update("reviewer_notes", event.target.value)} /></label>
          <label className="wide-field">Correction Reason<textarea value={form.correction_reason} onChange={(event) => update("correction_reason", event.target.value)} /></label>
          <button className="primary-button" onClick={() => onSaveFeedback(result, form)} disabled={!activeEvaluationId}>Save Feedback</button>
        </div>
      )}
    </div>
  );
}

export default function DatasetEvaluation({ user, workspaceId }) {
  const [cases, setCases] = useState([]);
  const [evaluation, setEvaluation] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [datasetName, setDatasetName] = useState("");
  const [datasetDescription, setDatasetDescription] = useState("");
  const [datasetVersion, setDatasetVersion] = useState("1.0");
  const [library, setLibrary] = useState([]);
  const [history, setHistory] = useState([]);
  const [feedbackHistory, setFeedbackHistory] = useState([]);
  const [feedbackByCase, setFeedbackByCase] = useState({});
  const [feedbackSummary, setFeedbackSummary] = useState(null);
  const [activeEvaluationId, setActiveEvaluationId] = useState("");
  const [activeDatasetId, setActiveDatasetId] = useState("");
  const [humanReviewMode, setHumanReviewMode] = useState(false);
  const [useHybridEvaluation, setUseHybridEvaluation] = useState(false);
  const [evaluationMode, setEvaluationMode] = useState("rule_based");
  const [viewedDataset, setViewedDataset] = useState(null);
  const [baseEvaluationId, setBaseEvaluationId] = useState("");
  const [currentEvaluationId, setCurrentEvaluationId] = useState("");
  const [comparison, setComparison] = useState(null);
  const [rootCauseReport, setRootCauseReport] = useState(null);
  const [timelineReport, setTimelineReport] = useState(null);
  const [impactGraphReport, setImpactGraphReport] = useState(null);
  const [sourceLabel, setSourceLabel] = useState("");
  const [loadingDataset, setLoadingDataset] = useState(false);
  const [runningEvaluation, setRunningEvaluation] = useState(false);
  const [previewingUpload, setPreviewingUpload] = useState(false);
  const [evaluatingUpload, setEvaluatingUpload] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [filters, setFilters] = useState({ correctness: "all", severity: "all", driftType: "all", label: "all" });

  useEffect(() => {
    refreshLibrary();
    refreshHistory();
    refreshFeedbackHistory();
  }, [workspaceId]);

  const filteredResults = useMemo(() => {
    if (!evaluation) return [];
    return evaluation.results.filter((result) => {
      const correct = result.overall_correct ?? result.passed;
      if (filters.correctness === "correct" && !correct) return false;
      if (filters.correctness === "incorrect" && correct) return false;
      if (filters.severity !== "all" && result.expected_severity !== filters.severity && result.predicted_severity !== filters.severity) return false;
      if (filters.driftType !== "all" && result.expected_drift_type !== filters.driftType && result.predicted_drift_type !== filters.driftType) return false;
      if (filters.label !== "all" && result.expected_label !== filters.label && result.predicted_label !== filters.label) return false;
      return true;
    });
  }, [evaluation, filters]);

  function showError(message) {
    if (message.includes("Dataset JSON must be a list")) {
      setError("Invalid dataset format. Please upload a JSON array of dataset cases.");
      return;
    }
    setError(message || "Dataset evaluation failed. Please check backend server.");
  }

  async function refreshLibrary() {
    try {
      setLibrary(await getDatasetLibrary());
    } catch {
      setLibrary([]);
    }
  }

  async function refreshHistory() {
    try {
      const items = await getEvaluationHistory();
      setHistory(items);
      if (items.length > 0) {
        setBaseEvaluationId((current) => current || items[0].evaluation_id);
        setCurrentEvaluationId((current) => current || items[0].evaluation_id);
      }
      return items;
    } catch {
      setHistory([]);
      return [];
    }
  }

  async function refreshFeedbackHistory() {
    try {
      setFeedbackHistory(await getAllFeedback());
    } catch {
      setFeedbackHistory([]);
    }
  }

  async function loadFeedback(evaluationId) {
    if (!evaluationId) return;
    try {
      const items = await getFeedbackForEvaluation(evaluationId);
      setFeedbackByCase(Object.fromEntries(items.map((item) => [item.case_id, item])));
      setFeedbackSummary(await getFeedbackSummaryForEvaluation(evaluationId));
    } catch {
      setFeedbackByCase({});
      setFeedbackSummary(null);
    }
  }

  async function setLatestEvaluationContext(datasetIdHint = "") {
    const items = await refreshHistory();
    if (items.length > 0) {
      setActiveEvaluationId(items[0].evaluation_id);
      setActiveDatasetId(datasetIdHint || items[0].dataset_id);
      await loadFeedback(items[0].evaluation_id);
    }
  }

  async function loadDataset() {
    setLoadingDataset(true);
    setError("");
    try {
      setCases(await getSampleDataset());
      setEvaluation(null);
      setSourceLabel("Source: Built-in Sample Dataset");
    } catch (err) {
      showError(err.message);
    } finally {
      setLoadingDataset(false);
    }
  }

  async function evaluateSampleDataset() {
    if (!workspaceId) {
      setError("No workspace selected. Please create or select a workspace first.");
      return;
    }
    setRunningEvaluation(true);
    setError("");
    try {
      const response = await runDatasetEvaluation();
      setEvaluation(response);
      setSourceLabel("Source: Built-in Sample Dataset");
      await setLatestEvaluationContext("sample");
    } catch (err) {
      showError(err.message);
    } finally {
      setRunningEvaluation(false);
    }
  }

  async function previewUploadedDataset() {
    if (!selectedFile) {
      setError("Please select a JSON or SNLI JSONL dataset file first.");
      return;
    }
    setPreviewingUpload(true);
    setError("");
    try {
      setCases(await uploadDatasetPreview(selectedFile));
      setEvaluation(null);
      setSourceLabel(`Source: Uploaded Dataset: ${selectedFile.name}`);
    } catch (err) {
      showError(err.message);
    } finally {
      setPreviewingUpload(false);
    }
  }

  async function evaluateUploadedDataset() {
    if (!selectedFile) {
      setError("Please select a JSON or SNLI JSONL dataset file first.");
      return;
    }
    if (!workspaceId) {
      setError("No workspace selected. Please create or select a workspace first.");
      return;
    }
    setEvaluatingUpload(true);
    setError("");
    try {
      const response = await uploadDatasetEvaluate(selectedFile);
      setEvaluation(response);
      setSourceLabel(`Source: Uploaded Dataset: ${selectedFile.name}`);
      await setLatestEvaluationContext("uploaded_temp");
    } catch (err) {
      showError(err.message);
    } finally {
      setEvaluatingUpload(false);
    }
  }

  async function saveDataset() {
    if (!selectedFile) {
      setError("Please select a JSON or SNLI JSONL dataset file first.");
      return;
    }
    if (!workspaceId) {
      setError("No workspace selected. Please create or select a workspace first.");
      return;
    }
    if (!datasetName.trim()) {
      setError("Please enter a dataset name before saving.");
      return;
    }
    setError("");
    setSuccess("");
    try {
      const saved = await saveUploadedDataset(selectedFile, datasetName, datasetDescription, datasetVersion);
      setSuccess(`Saved dataset: ${saved.name}`);
      await refreshLibrary();
    } catch (err) {
      showError(err.message);
    }
  }

  async function viewDataset(datasetId) {
    setError("");
    try {
      const dataset = await getSavedDataset(datasetId);
      setViewedDataset(dataset);
      setCases(dataset.cases || []);
      setSourceLabel(`Source: Saved Dataset: ${dataset.metadata?.name || datasetId}`);
    } catch (err) {
      showError(err.message);
    }
  }

  async function runSavedDataset(dataset) {
    setError("");
    try {
      const response = await evaluateSavedDataset(dataset.dataset_id);
      setEvaluation(response);
      setSourceLabel(`Source: Saved Dataset: ${dataset.name}`);
      await setLatestEvaluationContext(dataset.dataset_id);
    } catch (err) {
      showError(err.message);
    }
  }

  async function removeSavedDataset(datasetId) {
    if (!confirm("Are you sure you want to delete this dataset?")) return;
    setError("");
    try {
      await deleteSavedDataset(datasetId);
      setViewedDataset(null);
      await refreshLibrary();
    } catch (err) {
      showError(err.message);
    }
  }

  async function viewEvaluationResult(evaluationId) {
    setError("");
    try {
      const payload = await getEvaluationResult(evaluationId);
      setEvaluation(payload.result);
      setSourceLabel(`Source: Evaluation History: ${payload.dataset_name}`);
      setActiveEvaluationId(evaluationId);
      setActiveDatasetId(payload.dataset_id);
      await loadFeedback(evaluationId);
    } catch (err) {
      showError(err.message);
    }
  }

  async function removeEvaluationResult(evaluationId) {
    if (!confirm("Are you sure you want to delete this evaluation result?")) return;
    setError("");
    try {
      await deleteEvaluationResult(evaluationId);
      await refreshHistory();
    } catch (err) {
      showError(err.message);
    }
  }

  async function saveFeedback(result, form) {
    if (!activeEvaluationId) {
      setError("Please run or view an evaluation first.");
      return;
    }
    setError("");
    try {
      await saveCaseFeedback({
        evaluation_id: activeEvaluationId,
        dataset_id: activeDatasetId || "unknown",
        case_id: result.case_id,
        original_expected_label: result.expected_label,
        original_predicted_label: result.predicted_label,
        corrected_label: form.corrected_label,
        original_expected_drift_type: result.expected_drift_type,
        original_predicted_drift_type: result.predicted_drift_type,
        corrected_drift_type: form.corrected_drift_type,
        original_expected_severity: result.expected_severity,
        original_predicted_severity: result.predicted_severity,
        corrected_severity: form.corrected_severity,
        review_status: form.review_status,
        reviewer_notes: form.reviewer_notes,
        correction_reason: form.correction_reason,
      });
      setSuccess(`Saved feedback for ${result.case_id}`);
      await loadFeedback(activeEvaluationId);
      await refreshFeedbackHistory();
    } catch (err) {
      showError(err.message);
    }
  }

  async function removeFeedback(feedbackId) {
    if (!confirm("Are you sure you want to delete this feedback?")) return;
    try {
      await deleteFeedback(feedbackId);
      await refreshFeedbackHistory();
      if (activeEvaluationId) await loadFeedback(activeEvaluationId);
    } catch (err) {
      showError(err.message);
    }
  }

  async function exportFeedbackArtifact(exporter) {
    if (!activeEvaluationId) {
      setError("Please run or view an evaluation first.");
      return;
    }
    try {
      await exporter(activeEvaluationId);
    } catch (err) {
      showError(err.message);
    }
  }

  async function generateLatestRootCause() {
    if (!evaluation) {
      setError("Please run or view an evaluation first.");
      return;
    }
    setError("");
    try {
      setRootCauseReport(await getLatestRootCauseReport());
    } catch (err) {
      showError(err.message);
    }
  }

  async function generateHistoryRootCause(evaluationId) {
    setError("");
    try {
      setRootCauseReport(await getRootCauseReportForEvaluation(evaluationId));
    } catch (err) {
      showError(err.message);
    }
  }

  async function generateLatestTimeline() {
    if (!evaluation) {
      setError("Please run or view an evaluation first.");
      return;
    }
    setError("");
    try {
      setTimelineReport(await getLatestTimeline());
    } catch (err) {
      showError(err.message);
    }
  }

  async function generateHistoryTimeline(evaluationId) {
    setError("");
    try {
      setTimelineReport(await getTimelineForEvaluation(evaluationId));
    } catch (err) {
      showError(err.message);
    }
  }

  async function generateLatestImpactGraph() {
    if (!evaluation) {
      setError("Please run or view an evaluation first.");
      return;
    }
    setError("");
    try {
      setImpactGraphReport(await getLatestImpactGraph());
    } catch (err) {
      showError(err.message);
    }
  }

  async function generateHistoryImpactGraph(evaluationId) {
    setError("");
    try {
      setImpactGraphReport(await getImpactGraphForEvaluation(evaluationId));
    } catch (err) {
      showError(err.message);
    }
  }

  const humanAccuracy = feedbackSummary
    ? {
        original: evaluation?.accuracy || 0,
        reviewedAccuracy: feedbackSummary.reviewed_cases
          ? Math.round((feedbackSummary.confirmed_correct_cases / feedbackSummary.reviewed_cases) * 100)
          : 0,
        confirmed: feedbackSummary.confirmed_correct_cases,
        corrected: feedbackSummary.corrected_cases,
      }
    : null;

  async function compareRuns() {
    if (!baseEvaluationId || !currentEvaluationId) {
      setError("Please select two evaluation runs to compare.");
      return;
    }
    setError("");
    try {
      setComparison(await compareEvaluations(baseEvaluationId, currentEvaluationId));
    } catch (err) {
      showError(err.message);
    }
  }

  async function exportReport(exporter) {
    if (!evaluation) {
      setError("Please run an evaluation first.");
      return;
    }
    setExporting(true);
    setError("");
    try {
      await exporter();
    } catch (err) {
      showError(err.message);
    } finally {
      setExporting(false);
    }
  }

  function downloadTemplate() {
    const blob = new Blob([JSON.stringify(datasetTemplate, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "driftguard-dataset-template.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h2>Dataset Evaluation</h2>
          <p>Evaluate DriftGuard AI using SNLI, CosQA, CommitPack, and Spider-inspired benchmark cases.</p>
        </div>
      </div>

      <section className="info-box">
        Dataset Evaluation helps test whether the system can correctly identify contradictions, no-drift cases, and manual-review cases. These sample cases are inspired by SNLI for contradiction detection, CosQA for code-text alignment, CommitPack for commit reasoning, and Spider for database/config verification.
      </section>

      <div className="dataset-control-grid">
        <section className="panel control-panel">
          <div>
            <h3>Built-in Dataset Controls</h3>
            <p>Use the bundled benchmark dataset to verify the local rule-based evaluator.</p>
          </div>
          <div className="control-actions">
            <button className="secondary-button" onClick={loadDataset} disabled={loadingDataset}>
              <Database size={17} />
              {loadingDataset ? "Loading dataset..." : "Load Sample Dataset"}
            </button>
            <PermissionGuard user={user} permission="run_evaluation">
              <button className="primary-button" onClick={evaluateSampleDataset} disabled={runningEvaluation || !workspaceId}>
                <PlayCircle size={17} />
                {runningEvaluation ? "Running evaluation..." : "Run Sample Evaluation"}
              </button>
            </PermissionGuard>
          </div>
        </section>

        <section className="panel control-panel upload-panel">
          <div>
            <h3>Upload Real Dataset</h3>
            <p>Upload a JSON or SNLI JSONL dataset file with real benchmark cases and evaluate DriftGuard AI on it.</p>
          </div>
          <label className="file-upload">
            <FileJson size={19} />
            <span>{selectedFile ? selectedFile.name : "Choose JSON or JSONL dataset file"}</span>
            <input type="file" accept=".json,.jsonl,application/json,application/jsonl" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} />
          </label>
          <div className="control-actions">
            <button className="secondary-button" onClick={downloadTemplate}><Download size={17} />Download Dataset Template</button>
            <button className="secondary-button" onClick={previewUploadedDataset} disabled={previewingUpload}>
              <Upload size={17} />{previewingUpload ? "Previewing..." : "Preview Uploaded Dataset"}
            </button>
            <PermissionGuard user={user} permission="run_evaluation">
              <button className="primary-button" onClick={evaluateUploadedDataset} disabled={evaluatingUpload || !workspaceId}>
                <PlayCircle size={17} />{evaluatingUpload ? "Running evaluation..." : "Evaluate Uploaded Dataset"}
              </button>
            </PermissionGuard>
          </div>
        </section>
      </div>

      {sourceLabel && <div className="source-strip">{sourceLabel}</div>}
      <section className="panel control-panel">
        <label>Evaluation Mode<select value={evaluationMode} onChange={(event) => { setEvaluationMode(event.target.value); setUseHybridEvaluation(event.target.value === "hybrid"); }}>
          <option value="rule_based">rule_based</option>
          <option value="deployed_ml">deployed_ml</option>
          <option value="hybrid">hybrid</option>
        </select></label>
        <p className="muted">Rule-based evaluation remains the default. Deployed ML and hybrid modes are available for reviewer comparison and future routed evaluation.</p>
      </section>
      {error && <div className="error-banner">{error}</div>}
      {success && <div className="success-banner">{success}</div>}

      <PermissionGuard user={user} permission="save_dataset">
      <section className="panel control-panel">
        <div>
          <h3>Save Uploaded Dataset</h3>
          <p>Store the selected JSON or SNLI JSONL dataset locally for repeatable benchmark runs.</p>
        </div>
        <div className="save-grid">
          <label>Dataset Name<input value={datasetName} onChange={(event) => setDatasetName(event.target.value)} placeholder="My Benchmark Dataset" /></label>
          <label>Description<input value={datasetDescription} onChange={(event) => setDatasetDescription(event.target.value)} placeholder="Optional description" /></label>
          <label>Version<input value={datasetVersion} onChange={(event) => setDatasetVersion(event.target.value)} placeholder="1.0" /></label>
          <button className="primary-button" onClick={saveDataset} disabled={!workspaceId}>Save Uploaded Dataset</button>
        </div>
      </section>
      </PermissionGuard>

      <section className="panel">
        <div className="section-heading"><h3>Saved Dataset Library</h3></div>
        {library.length === 0 ? <p className="empty-state">No saved datasets yet.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Version</th><th>Created</th><th>Total Cases</th><th>Quality</th><th>Labels</th><th>Actions</th></tr></thead>
              <tbody>
                {library.map((dataset) => (
                  <tr key={dataset.dataset_id}>
                    <td>{dataset.name}</td>
                    <td>{dataset.version}</td>
                    <td>{new Date(dataset.created_at).toLocaleString()}</td>
                    <td>{dataset.total_cases}</td>
                    <td>{dataset.quality_score}</td>
                    <td>{objectEntries(dataset.label_distribution).map(([key, value]) => `${key}: ${value}`).join(", ")}</td>
                    <td>
                      <div className="row-actions">
                        <button className="secondary-button" onClick={() => viewDataset(dataset.dataset_id)}>View</button>
                        <PermissionGuard user={user} permission="run_evaluation"><button className="secondary-button" onClick={() => runSavedDataset(dataset)}>Evaluate</button></PermissionGuard>
                        <PermissionGuard user={user} permission="delete_dataset"><button className="secondary-button danger-button" onClick={() => removeSavedDataset(dataset.dataset_id)}>Delete</button></PermissionGuard>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {viewedDataset && (
        <section className="panel">
          <div className="section-heading">
            <h3>Saved Dataset Details</h3>
            <span className="source-badge">{viewedDataset.metadata.name} v{viewedDataset.metadata.version}</span>
          </div>
          <DatasetQualityCard report={{
            total_cases: viewedDataset.metadata.total_cases,
            valid_cases: viewedDataset.metadata.total_cases,
            invalid_cases: 0,
            label_distribution: viewedDataset.metadata.label_distribution,
            drift_type_distribution: viewedDataset.metadata.drift_type_distribution,
            severity_distribution: viewedDataset.metadata.severity_distribution,
            quality_score: viewedDataset.metadata.quality_score,
            missing_field_warnings: [],
            empty_field_warnings: [],
          }} />
        </section>
      )}

      <DatasetTable cases={cases} sourceLabel={sourceLabel} />

      {evaluation && (
        <div className="results-stack">
          {useHybridEvaluation && (
            <HybridReasoningPanel
              taskType="contradiction_detection"
              inputContext={evaluation.results?.[0]?.input || {}}
              workspaceId={workspaceId}
            />
          )}
          <EvaluationCards evaluation={evaluation} />
          <DatasetQualityCard report={evaluation.dataset_quality_report} />
          <AccuracyBreakdown evaluation={evaluation} />
          <section className="panel insights-panel">
            <div className="section-heading"><h3>Summary Insights</h3></div>
            <ul>{evaluation.summary_insights.map((insight) => <li key={insight}>{insight}</li>)}</ul>
          </section>
          <div className="matrix-grid">
            <MatrixTable title="Label Confusion Matrix" matrix={evaluation.confusion_matrix.labels} />
            <MatrixTable title="Drift Type Confusion Matrix" matrix={evaluation.confusion_matrix.drift_type} />
            <MatrixTable title="Severity Confusion Matrix" matrix={evaluation.confusion_matrix.severity} />
          </div>
          <Filters filters={filters} setFilters={setFilters} results={evaluation.results} />
          <PermissionGuard user={user} permission="add_feedback">
          <section className="panel export-panel">
            <div>
              <h3>Human Review Mode</h3>
              <p>Review individual cases, correct labels, and save human feedback.</p>
            </div>
            <button className={humanReviewMode ? "primary-button" : "secondary-button"} onClick={() => setHumanReviewMode(!humanReviewMode)}>
              Human Review Mode
            </button>
          </section>
          </PermissionGuard>
          {feedbackSummary && (
            <section className="panel">
              <div className="section-heading"><h3>Feedback Summary</h3></div>
              <div className="evaluation-grid">
                <div className="metric-card compact"><span>Reviewed</span><strong>{feedbackSummary.reviewed_cases}</strong></div>
                <div className="metric-card compact"><span>Unreviewed</span><strong>{feedbackSummary.unreviewed_cases}</strong></div>
                <div className="metric-card compact"><span>Corrected</span><strong>{feedbackSummary.corrected_cases}</strong></div>
                <div className="metric-card compact"><span>Confirmed Correct</span><strong>{feedbackSummary.confirmed_correct_cases}</strong></div>
                <div className="metric-card compact"><span>Completion</span><strong>{feedbackSummary.human_review_completion_percentage}%</strong></div>
                <div className="metric-card compact"><span>Common Correction</span><strong>{feedbackSummary.most_common_correction_type}</strong></div>
                <div className="metric-card compact"><span>Reviewed Accuracy</span><strong>{humanAccuracy.reviewedAccuracy}%</strong></div>
              </div>
              <p className="empty-state">Original accuracy: {humanAccuracy.original}% | Confirmed by human: {humanAccuracy.confirmed} | Corrected by human: {humanAccuracy.corrected}</p>
            </section>
          )}
          <section className="panel">
            <div className="section-heading">
              <h3>Evaluation Results</h3>
              <span className="source-badge">{filteredResults.length} shown</span>
            </div>
            <div className="case-results">
              {filteredResults.map((result) => (
                <ResultDetails
                  key={result.case_id}
                  result={result}
                  humanReviewMode={humanReviewMode}
                  feedback={feedbackByCase[result.case_id]}
                  onSaveFeedback={saveFeedback}
                  activeEvaluationId={activeEvaluationId}
                />
              ))}
            </div>
          </section>
          <PermissionGuard user={user} permission="export_reports">
          <section className="panel export-panel">
            <div>
              <h3>Root Cause Analysis</h3>
              <p>Generate rule-based root cause, owner, priority, and fix recommendations for this evaluation.</p>
            </div>
            <button className="primary-button" onClick={generateLatestRootCause}>Generate Root Cause Analysis</button>
          </section>
          </PermissionGuard>
          <RootCauseDashboard report={rootCauseReport} onError={showError} workspaceId={workspaceId} />
          <section className="panel export-panel">
            <div>
              <h3>Drift Timeline</h3>
              <p>Build an inferred event timeline across Jira, docs, commits, code, config, logs, and evaluation output.</p>
            </div>
            <button className="primary-button" onClick={generateLatestTimeline}>Generate Drift Timeline</button>
          </section>
          <TimelineDashboard report={timelineReport} onError={showError} />
          <section className="panel export-panel">
            <div>
              <h3>Impact Graph</h3>
              <p>Map source relationships and affected components for this evaluation.</p>
            </div>
            <button className="primary-button" onClick={generateLatestImpactGraph}>Generate Impact Graph</button>
          </section>
          <ImpactGraphDashboard report={impactGraphReport} onError={showError} />
          <section className="panel export-panel">
            <div>
              <h3>Export Report</h3>
              <p>Download the latest evaluation report for sharing or review.</p>
            </div>
            <div className="control-actions">
              <button className="secondary-button" onClick={() => exportReport(exportLatestEvaluationJson)} disabled={exporting}>
                <Download size={17} />Export JSON Report
              </button>
              <button className="secondary-button" onClick={() => exportReport(exportLatestEvaluationMarkdown)} disabled={exporting}>
                <Download size={17} />Export Markdown Report
              </button>
            </div>
          </section>
        </div>
      )}

      <section className="panel">
        <div className="section-heading"><h3>Evaluation History</h3></div>
        {history.length === 0 ? <p className="empty-state">No evaluation history yet.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Evaluation ID</th><th>Dataset</th><th>Created</th><th>Total</th><th>Accuracy</th><th>Label</th><th>Drift Type</th><th>Severity</th><th>Quality</th><th>Actions</th></tr></thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.evaluation_id}>
                    <td>{item.evaluation_id.slice(0, 8)}</td>
                    <td>{item.dataset_name}</td>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td>{item.total_cases}</td>
                    <td>{item.accuracy}%</td>
                    <td>{item.label_accuracy}%</td>
                    <td>{item.drift_type_accuracy}%</td>
                    <td>{item.severity_accuracy}%</td>
                    <td>{item.quality_score}</td>
                    <td>
                      <div className="row-actions">
                        <button className="secondary-button" onClick={() => viewEvaluationResult(item.evaluation_id)}>View Result</button>
                        <button className="secondary-button" onClick={() => generateHistoryRootCause(item.evaluation_id)}>Root Cause</button>
                        <button className="secondary-button" onClick={() => generateHistoryTimeline(item.evaluation_id)}>Timeline</button>
                        <button className="secondary-button" onClick={() => generateHistoryImpactGraph(item.evaluation_id)}>Impact Graph</button>
                        <PermissionGuard user={user} permission="delete_history"><button className="secondary-button danger-button" onClick={() => removeEvaluationResult(item.evaluation_id)}>Delete</button></PermissionGuard>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-heading">
          <h3>Human Feedback History</h3>
          <button className="secondary-button" onClick={refreshFeedbackHistory}>Refresh Feedback History</button>
        </div>
        {feedbackHistory.length === 0 ? <p className="empty-state">No feedback saved yet.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Feedback ID</th><th>Evaluation ID</th><th>Case ID</th><th>Label</th><th>Drift Type</th><th>Severity</th><th>Status</th><th>Created</th><th>Action</th></tr></thead>
              <tbody>
                {feedbackHistory.map((item) => (
                  <tr key={item.feedback_id}>
                    <td>{item.feedback_id.slice(0, 8)}</td>
                    <td>{item.evaluation_id.slice(0, 8)}</td>
                    <td>{item.case_id}</td>
                    <td>{item.corrected_label}</td>
                    <td>{item.corrected_drift_type}</td>
                    <td>{item.corrected_severity}</td>
                    <td><span className={item.review_status === "reviewed" ? "badge passed" : "badge neutral"}>{item.review_status}</span></td>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td><PermissionGuard user={user} permission="add_feedback"><button className="secondary-button danger-button" onClick={() => removeFeedback(item.feedback_id)}>Delete</button></PermissionGuard></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Compare Evaluation Runs</h3></div>
        <div className="filters-grid">
          <label>Base Evaluation<select value={baseEvaluationId} onChange={(event) => setBaseEvaluationId(event.target.value)}>{history.map((item) => <option key={item.evaluation_id} value={item.evaluation_id}>{item.dataset_name} - {item.evaluation_id.slice(0, 8)}</option>)}</select></label>
          <label>Current Evaluation<select value={currentEvaluationId} onChange={(event) => setCurrentEvaluationId(event.target.value)}>{history.map((item) => <option key={item.evaluation_id} value={item.evaluation_id}>{item.dataset_name} - {item.evaluation_id.slice(0, 8)}</option>)}</select></label>
          <button className="primary-button" onClick={compareRuns}>Compare</button>
        </div>
        {comparison && (
          <div className={comparison.has_regression ? "regression-card bad" : "regression-card good"}>
            <span className={comparison.has_regression ? "badge failed" : "badge passed"}>{comparison.has_regression ? "Regression Detected" : "No Regression"}</span>
            <p>{comparison.has_regression ? "Regression detected. Current evaluation is worse than base evaluation." : "No regression detected. Current evaluation is stable or improved."}</p>
            <p>{comparison.regression_summary}</p>
            <div className="comparison-grid">
              <div><span>Accuracy Delta</span><p>{comparison.accuracy_delta}</p></div>
              <div><span>Label Delta</span><p>{comparison.label_accuracy_delta}</p></div>
              <div><span>Drift Type Delta</span><p>{comparison.drift_type_accuracy_delta}</p></div>
              <div><span>Severity Delta</span><p>{comparison.severity_accuracy_delta}</p></div>
              <div><span>Quality Delta</span><p>{comparison.quality_score_delta}</p></div>
            </div>
            <p><strong>Newly failed:</strong> {comparison.newly_failed_cases.join(", ") || "None"}</p>
            <p><strong>Newly passed:</strong> {comparison.newly_passed_cases.join(", ") || "None"}</p>
            <p><strong>Unchanged failed:</strong> {comparison.unchanged_failed_cases.join(", ") || "None"}</p>
          </div>
        )}
      </section>

      <PermissionGuard user={user} permission="export_reports">
      <section className="panel export-panel">
        <div>
          <h3>Human-Corrected Exports</h3>
          <p>Export corrected benchmark cases or a training-ready dataset from the active evaluation.</p>
        </div>
        <div className="control-actions">
          <button className="secondary-button" onClick={() => exportFeedbackArtifact(exportCorrectedDataset)}>Export Corrected Dataset</button>
          <button className="secondary-button" onClick={() => exportFeedbackArtifact(buildTrainingDataset)}>Build Training Dataset</button>
        </div>
      </section>
      </PermissionGuard>
    </section>
  );
}
