import { Download, Play, RefreshCw, Rocket, RotateCcw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import {
  compareModelExperiments,
  deleteModelExperiment,
  deployModelExperiment,
  exportModelExperimentMarkdown,
  getBenchmarkDatasets,
  getDeployedModels,
  getModelExperiment,
  getModelLeaderboard,
  getTrainingExports,
  predictWithMLModel,
  rollbackDeployedModel,
  trainModelExperiment,
} from "../api.js";

const taskTypes = ["label_classification", "severity_classification", "drift_type_classification"];
const modelTypes = ["logistic_regression", "linear_svm", "naive_bayes", "random_forest"];

function Badge({ value }) {
  const key = String(value || "").toLowerCase();
  const kind = key === "completed" || key === "active" ? "success" : key === "failed" || key === "rolled_back" ? "failed" : key === "running" || key === "fallback" ? "warning" : "neutral";
  return <span className={`badge ${kind}`}>{value || "none"}</span>;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

function Metric({ label, value }) {
  return <div className="metric-card compact"><span>{label}</span><strong>{value ?? 0}</strong></div>;
}

export default function ModelTrainingDashboard({ user, workspaceId }) {
  const [exportsList, setExportsList] = useState([]);
  const [benchmarks, setBenchmarks] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [deployed, setDeployed] = useState([]);
  const [selected, setSelected] = useState(null);
  const [compare, setCompare] = useState({ base_id: "", current_id: "" });
  const [compareResult, setCompareResult] = useState(null);
  const [predictionInput, setPredictionInput] = useState({ task_type: "label_classification", documentation: "", code: "", jira: "", commit: "", logs: "", database_config: "" });
  const [prediction, setPrediction] = useState(null);
  const [form, setForm] = useState({
    name: "DriftGuard Label Classifier",
    task_type: "label_classification",
    model_type: "logistic_regression",
    training_export_id: "",
    benchmark_ids: [],
    include_human_corrected: true,
    max_examples: 5000,
    test_size: 0.2,
    random_seed: 42,
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canTrain = ["admin", "engineer"].includes(user?.role);
  const canAdmin = user?.role === "admin";

  async function refresh(taskType = form.task_type) {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const [nextExports, nextBenchmarks, nextLeaderboard, nextDeployed] = await Promise.all([
        getTrainingExports(workspaceId),
        getBenchmarkDatasets(workspaceId),
        getModelLeaderboard(workspaceId, taskType),
        getDeployedModels(workspaceId),
      ]);
      setExportsList(nextExports);
      setBenchmarks(nextBenchmarks);
      setLeaderboard(nextLeaderboard);
      setDeployed(nextDeployed);
      if (!form.training_export_id && nextExports[0]?.export_id) {
        setForm((current) => ({ ...current, training_export_id: nextExports[0].export_id }));
      }
    } catch (err) {
      setError(err.message || "Unable to load model data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [workspaceId]);

  async function startTraining(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!form.training_export_id && form.benchmark_ids.length === 0 && !form.include_human_corrected) {
      setError("Select a training export, benchmark dataset, or include human-corrected examples before training.");
      return;
    }
    try {
      const result = await trainModelExperiment({ ...form, workspace_id: workspaceId, max_examples: Number(form.max_examples), test_size: Number(form.test_size), random_seed: Number(form.random_seed) });
      setMessage(`Training finished: F1 ${result.experiment?.f1_macro ?? 0}.`);
      await refresh(form.task_type);
      setSelected(result);
    } catch (err) {
      setError(err.message || "Training failed.");
    }
  }

  async function viewExperiment(experimentId) {
    setSelected(await getModelExperiment(experimentId));
  }

  async function deployExperiment(experimentId) {
    await deployModelExperiment(experimentId);
    setMessage("Model deployed. Rule-based fallback remains available through rollback.");
    await refresh(form.task_type);
  }

  async function removeExperiment(experimentId) {
    if (!confirm("Delete this experiment and its artifact?")) return;
    await deleteModelExperiment(experimentId);
    setSelected(null);
    await refresh(form.task_type);
  }

  async function compareExperiments() {
    setCompareResult(await compareModelExperiments(compare.base_id, compare.current_id));
  }

  async function rollback(taskType) {
    await rollbackDeployedModel(taskType, workspaceId);
    setMessage("Model rolled back. Rule-based fallback is active for this task.");
    await refresh(form.task_type);
  }

  async function runPrediction() {
    const { task_type, ...input_context } = predictionInput;
    setPrediction(await predictWithMLModel({ workspace_id: workspaceId, task_type, input_context }));
  }

  function toggleBenchmark(benchmarkId) {
    const next = form.benchmark_ids.includes(benchmarkId)
      ? form.benchmark_ids.filter((item) => item !== benchmarkId)
      : [...form.benchmark_ids, benchmarkId];
    setForm({ ...form, benchmark_ids: next });
  }

  return (
    <section className="page model-page">
      <div className="page-header">
        <div>
          <h2>Model Training Sandbox</h2>
          <p>Train lightweight local baseline models on DriftGuard training data. Compare experiments, deploy selected models, and keep rule-based fallback.</p>
        </div>
        <button className="secondary-button" onClick={() => refresh()} disabled={loading}><RefreshCw size={16} />Refresh</button>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        <div className="section-heading"><h3><Play size={18} /> Start Training Experiment</h3></div>
        <form className="filter-row" onSubmit={startTraining}>
          <label>Experiment name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
          <label>Task type<select value={form.task_type} onChange={(event) => { setForm({ ...form, task_type: event.target.value }); refresh(event.target.value); }}>{taskTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Model type<select value={form.model_type} onChange={(event) => setForm({ ...form, model_type: event.target.value })}>{modelTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Training export<select value={form.training_export_id} onChange={(event) => setForm({ ...form, training_export_id: event.target.value })}><option value="">None</option>{exportsList.map((item) => <option key={item.export_id} value={item.export_id}>{item.name}</option>)}</select></label>
          <label>Max examples<input type="number" min="10" value={form.max_examples} onChange={(event) => setForm({ ...form, max_examples: event.target.value })} /></label>
          <label>Test size<input type="number" min="0.1" max="0.5" step="0.05" value={form.test_size} onChange={(event) => setForm({ ...form, test_size: event.target.value })} /></label>
          <label>Random seed<input type="number" value={form.random_seed} onChange={(event) => setForm({ ...form, random_seed: event.target.value })} /></label>
          <label className="checkbox-label"><input type="checkbox" checked={form.include_human_corrected} onChange={(event) => setForm({ ...form, include_human_corrected: event.target.checked })} />Include human-corrected examples</label>
          <button className="primary-button" disabled={!canTrain || !workspaceId}>Start Training</button>
        </form>
        {!exportsList.length && !benchmarks.length && (
          <div className="warning-banner">No training exports or benchmark datasets found. Open Training Data, import at least 10 labeled examples across 2 classes, then export a training dataset.</div>
        )}
        <div className="agent-log">
          {benchmarks.map((item) => (
            <label className="checkbox-label" key={item.benchmark_id}>
              <input type="checkbox" checked={form.benchmark_ids.includes(item.benchmark_id)} onChange={() => toggleBenchmark(item.benchmark_id)} />
              {item.name} <Badge value={item.dataset_type} />
            </label>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Experiment Leaderboard</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Rank</th><th>Name</th><th>Task</th><th>Model</th><th>Status</th><th>Accuracy</th><th>F1</th><th>Precision</th><th>Recall</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>
              {leaderboard.map((item, index) => (
                <tr key={item.experiment_id}>
                  <td>{index + 1}</td>
                  <td>{item.name}</td>
                  <td>{item.task_type}</td>
                  <td>{item.model_type}</td>
                  <td><Badge value={item.status} /></td>
                  <td>{item.accuracy}</td>
                  <td>{item.f1_macro}</td>
                  <td>{item.precision_macro}</td>
                  <td>{item.recall_macro}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td className="button-row">
                    <button className="secondary-button" onClick={() => viewExperiment(item.experiment_id)}>View</button>
                    <button className="secondary-button" onClick={() => deployExperiment(item.experiment_id)} disabled={!canTrain}><Rocket size={16} />Deploy</button>
                    <button className="secondary-button" onClick={() => exportModelExperimentMarkdown(item.experiment_id)}><Download size={16} />Report</button>
                    {canAdmin && <button className="secondary-button danger" onClick={() => removeExperiment(item.experiment_id)}><Trash2 size={16} />Delete</button>}
                  </td>
                </tr>
              ))}
              {!leaderboard.length && <tr><td colSpan="11">No completed model experiments yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      {selected?.experiment && (
        <section className="panel">
          <div className="section-heading"><h3>Experiment Detail <Badge value={selected.experiment.status} /></h3></div>
          <div className="evaluation-grid">
            <Metric label="Accuracy" value={selected.experiment.accuracy} />
            <Metric label="F1 macro" value={selected.experiment.f1_macro} />
            <Metric label="Precision" value={selected.experiment.precision_macro} />
            <Metric label="Recall" value={selected.experiment.recall_macro} />
          </div>
          <pre className="json-block">{JSON.stringify(selected.experiment.confusion_matrix, null, 2)}</pre>
          <div className="agent-log">{selected.experiment.training_log?.map((item) => <div className="agent-log-row" key={item}><strong>Log</strong><p>{item}</p></div>)}</div>
        </section>
      )}

      <section className="panel">
        <div className="section-heading"><h3>Compare Experiments</h3></div>
        <div className="filter-row">
          <label>Base experiment<select value={compare.base_id} onChange={(event) => setCompare({ ...compare, base_id: event.target.value })}><option value="">Select</option>{leaderboard.map((item) => <option key={item.experiment_id} value={item.experiment_id}>{item.name}</option>)}</select></label>
          <label>Current experiment<select value={compare.current_id} onChange={(event) => setCompare({ ...compare, current_id: event.target.value })}><option value="">Select</option>{leaderboard.map((item) => <option key={item.experiment_id} value={item.experiment_id}>{item.name}</option>)}</select></label>
          <button className="secondary-button" onClick={compareExperiments} disabled={!compare.base_id || !compare.current_id}>Compare</button>
        </div>
        {compareResult && <div className="evaluation-grid"><Metric label="Accuracy delta" value={compareResult.accuracy_delta} /><Metric label="F1 delta" value={compareResult.f1_delta} /><Metric label="Precision delta" value={compareResult.precision_delta} /><Metric label="Recall delta" value={compareResult.recall_delta} /></div>}
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Deployed Models</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Task</th><th>Experiment</th><th>Model</th><th>Status</th><th>Deployed at</th><th>Actions</th></tr></thead>
            <tbody>
              {deployed.map((item) => (
                <tr key={item.deployed_model_id}>
                  <td>{item.task_type}</td>
                  <td className="mono-cell">{item.experiment_id}</td>
                  <td>{item.model_type}</td>
                  <td><Badge value={item.status} /></td>
                  <td>{formatDate(item.deployed_at)}</td>
                  <td>{canAdmin && item.status === "active" && <button className="secondary-button" onClick={() => rollback(item.task_type)}><RotateCcw size={16} />Rollback</button>}</td>
                </tr>
              ))}
              {!deployed.length && <tr><td colSpan="6">No deployed models yet. Rule-based engine is the fallback.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Test Prediction</h3></div>
        <div className="filter-row">
          <label>Task type<select value={predictionInput.task_type} onChange={(event) => setPredictionInput({ ...predictionInput, task_type: event.target.value })}>{taskTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
          {["documentation", "code", "jira", "commit", "logs", "database_config"].map((key) => (
            <label key={key}>{key.replace("_", " ")}<textarea value={predictionInput[key]} onChange={(event) => setPredictionInput({ ...predictionInput, [key]: event.target.value })} /></label>
          ))}
          <button className="primary-button" onClick={runPrediction}>Run Prediction</button>
        </div>
        {prediction && <div className="evaluation-grid"><Metric label="Prediction" value={prediction.prediction || "fallback"} /><Metric label="Confidence" value={prediction.confidence ?? "n/a"} /><Metric label="Model" value={prediction.model_type || "rule_based"} /><Metric label="Fallback used" value={prediction.fallback_used ? "yes" : "no"} /></div>}
      </section>
    </section>
  );
}
