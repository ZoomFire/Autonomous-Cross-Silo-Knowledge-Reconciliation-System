import { Download, Layers3, RefreshCw, Scissors, Trash2, UploadCloud } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  createBenchmarkSplit,
  createDriftGuardDatasetFromBenchmark,
  deleteBenchmarkDataset,
  downloadTrainingExport,
  exportTrainingDataset,
  getBenchmarkDatasets,
  getBenchmarkExamples,
  getBenchmarkQuality,
  getBenchmarkRegistry,
  getTrainingExports,
  mergeTrainingData,
  uploadBenchmarkDataset,
} from "../api.js";

const defaultUpload = { dataset_type: "snli", name: "", description: "" };

function Badge({ value }) {
  const key = String(value || "").toLowerCase();
  const kind = key.includes("fail") || key === "contradiction" ? "failed" : key.includes("partial") || key === "uncertain" ? "warning" : key.includes("train") || key.includes("import") || key === "no_contradiction" ? "success" : "neutral";
  return <span className={`badge ${kind}`}>{value || "none"}</span>;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Unknown";
}

function Distribution({ title, data = {} }) {
  const entries = Object.entries(data);
  return (
    <div className="metric-card compact">
      <span>{title}</span>
      <div className="distribution-list">
        {entries.length ? entries.map(([key, value]) => (
          <p key={key}>
            <strong title={key}>{key}</strong>
            <span>{value}</span>
          </p>
        )) : <p>No data yet.</p>}
      </div>
    </div>
  );
}

function textPreview(value = {}) {
  const raw = typeof value === "string" ? value : JSON.stringify(value);
  return raw.length > 160 ? `${raw.slice(0, 160)}...` : raw;
}

export default function BenchmarkTrainingDashboard({ user, workspaceId }) {
  const [registry, setRegistry] = useState({});
  const [datasets, setDatasets] = useState([]);
  const [examples, setExamples] = useState([]);
  const [quality, setQuality] = useState(null);
  const [exports, setExports] = useState([]);
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState("");
  const [filters, setFilters] = useState({ split: "", label: "" });
  const [upload, setUpload] = useState(defaultUpload);
  const [file, setFile] = useState(null);
  const [mergeOptions, setMergeOptions] = useState({ include_human_corrected: true, max_examples: 1000 });
  const [mergeSummary, setMergeSummary] = useState(null);
  const [exportForm, setExportForm] = useState({ name: "DriftGuard Training Export v1", description: "", format: "jsonl" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canManage = ["admin", "engineer"].includes(user?.role);
  const canDelete = user?.role === "admin";
  const selectedIds = useMemo(() => datasets.map((item) => item.benchmark_id), [datasets]);
  const selectedDataset = datasets.find((item) => item.benchmark_id === selectedBenchmarkId);

  async function refresh() {
    if (!workspaceId) return;
    setLoading(true);
    setError("");
    try {
      const [nextRegistry, nextDatasets, nextExports] = await Promise.all([
        getBenchmarkRegistry(),
        getBenchmarkDatasets(workspaceId),
        getTrainingExports(workspaceId),
      ]);
      setRegistry(nextRegistry);
      setDatasets(nextDatasets);
      setExports(nextExports);
      const nextSelected = selectedBenchmarkId || nextDatasets[0]?.benchmark_id || "";
      setSelectedBenchmarkId(nextSelected);
      if (nextSelected) {
        await loadBenchmarkDetail(nextSelected);
      }
    } catch (err) {
      setError(err.message || "Unable to load benchmark data.");
    } finally {
      setLoading(false);
    }
  }

  async function loadBenchmarkDetail(benchmarkId = selectedBenchmarkId, nextFilters = filters) {
    if (!benchmarkId) {
      setExamples([]);
      setQuality(null);
      return;
    }
    const [nextExamples, nextQuality] = await Promise.all([
      getBenchmarkExamples(benchmarkId, { ...nextFilters, limit: 50 }),
      getBenchmarkQuality(benchmarkId),
    ]);
    setExamples(nextExamples);
    setQuality(nextQuality);
  }

  useEffect(() => {
    refresh();
  }, [workspaceId]);

  async function submitUpload(event) {
    event.preventDefault();
    if (!file) {
      setError("Choose a benchmark file first.");
      return;
    }
    setError("");
    setMessage("");
    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("dataset_type", upload.dataset_type);
    formData.append("name", upload.name || `${upload.dataset_type.toUpperCase()} Benchmark`);
    formData.append("description", upload.description);
    formData.append("file", file);
    const result = await uploadBenchmarkDataset(formData);
    setMessage(result.import_run?.summary || "Benchmark imported.");
    setSelectedBenchmarkId(result.benchmark?.benchmark_id || "");
    await refresh();
  }

  async function chooseBenchmark(benchmarkId) {
    setSelectedBenchmarkId(benchmarkId);
    await loadBenchmarkDetail(benchmarkId);
  }

  async function updateFilter(key, value) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    await loadBenchmarkDetail(selectedBenchmarkId, next);
  }

  async function splitBenchmark(benchmarkId) {
    try {
      setError("");
      const result = await createBenchmarkSplit(benchmarkId, { train_ratio: 0.8, validation_ratio: 0.1, test_ratio: 0.1, seed: 42 });
      setMessage(`Split created: train ${result.split_counts.train}, validation ${result.split_counts.validation}, test ${result.split_counts.test}.`);
      await loadBenchmarkDetail(benchmarkId);
      await refresh();
    } catch (err) {
      setError(err.message || "Unable to create split.");
    }
  }

  async function convertBenchmark(benchmark) {
    try {
      setError("");
      const result = await createDriftGuardDatasetFromBenchmark(benchmark.benchmark_id, {
        dataset_name: `${benchmark.name} Converted Dataset`,
        description: `Converted ${benchmark.dataset_type} benchmark examples for DriftGuard evaluation.`,
        version: "1.0",
      });
      setMessage(`Created DriftGuard dataset: ${result.name}.`);
    } catch (err) {
      setError(err.message || "Unable to convert benchmark.");
    }
  }

  async function removeBenchmark(benchmarkId) {
    if (!confirm("Delete this benchmark dataset and imported examples?")) return;
    await deleteBenchmarkDataset(benchmarkId);
    setMessage("Benchmark dataset deleted.");
    setSelectedBenchmarkId("");
    await refresh();
  }

  async function previewMerge() {
    if (!selectedIds.length) {
      setError("Import or select at least one benchmark dataset before previewing training data.");
      return;
    }
    try {
      setError("");
      setMessage("");
      const result = await mergeTrainingData({
        workspace_id: workspaceId,
        benchmark_ids: selectedIds,
        include_human_corrected: mergeOptions.include_human_corrected,
        max_examples: Number(mergeOptions.max_examples || 1000),
      });
      setMergeSummary(result.summary);
      setMessage("Merged training data preview ready.");
    } catch (err) {
      setError(err.message || "Unable to preview merged training data.");
    }
  }

  async function submitExport() {
    if (!selectedIds.length) {
      setError("Import or select at least one benchmark dataset before exporting training data.");
      return;
    }
    try {
      setError("");
      setMessage("");
      const result = await exportTrainingDataset({
        ...exportForm,
        workspace_id: workspaceId,
        benchmark_ids: selectedIds,
        include_human_corrected: mergeOptions.include_human_corrected,
        max_examples: Number(mergeOptions.max_examples || 1000),
      });
      setMessage(`Export created: ${result.export.name}.`);
      setExports(await getTrainingExports(workspaceId));
    } catch (err) {
      setError(err.message || "Unable to export training dataset.");
    }
  }

  return (
    <section className="page benchmark-page">
      <div className="page-header">
        <div>
          <h2>Benchmark and Training Data Pipeline</h2>
          <p>Import public benchmark datasets like CosQA, SNLI, CommitPack, and Spider. Convert them into DriftGuard-compatible examples, analyze quality, create splits, and export training-ready JSONL.</p>
        </div>
        <button className="secondary-button" onClick={refresh} disabled={loading}><RefreshCw size={16} />Refresh</button>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        <div className="section-heading"><h3><Layers3 size={18} /> Dataset Registry</h3></div>
        <div className="dataset-registry-grid">
          {Object.entries(registry).map(([key, item]) => (
            <div className="dataset-registry-card" key={key}>
              <span>{item.name}</span>
              <strong title={item.output_task}>{item.output_task}</strong>
              <p>{item.purpose}</p>
              <p>{item.recommended_use}</p>
              <Badge value={(item.expected_formats || []).join(", ")} />
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3><UploadCloud size={18} /> Upload Benchmark Dataset</h3></div>
        <form className="filter-row" onSubmit={submitUpload}>
          <label>Dataset type<select value={upload.dataset_type} onChange={(event) => setUpload({ ...upload, dataset_type: event.target.value })}>{Object.keys(registry).map((key) => <option key={key} value={key}>{registry[key].name}</option>)}</select></label>
          <label>Dataset name<input value={upload.name} onChange={(event) => setUpload({ ...upload, name: event.target.value })} placeholder="SNLI Local Sample" /></label>
          <label>Description<input value={upload.description} onChange={(event) => setUpload({ ...upload, description: event.target.value })} placeholder="Small downloaded benchmark sample" /></label>
          <label>File<input type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
          <button className="primary-button" disabled={!canManage || !workspaceId}>Upload and Import Benchmark</button>
        </form>
        <p className="muted-text">Upload downloaded dataset files locally. DriftGuard does not require paid APIs.</p>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Benchmark Dataset List</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Examples</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>
              {datasets.map((item) => (
                <tr key={item.benchmark_id}>
                  <td>{item.name}</td>
                  <td><Badge value={item.dataset_type} /></td>
                  <td><Badge value={item.status} /></td>
                  <td>{item.imported_examples}/{item.total_examples}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td className="button-row">
                    <button className="secondary-button" onClick={() => chooseBenchmark(item.benchmark_id)}>View</button>
                    <button className="secondary-button" onClick={() => splitBenchmark(item.benchmark_id)} disabled={!canManage}><Scissors size={16} />Create Split</button>
                    <button className="secondary-button" onClick={() => convertBenchmark(item)} disabled={!canManage}>Convert</button>
                    {canDelete && <button className="secondary-button danger" onClick={() => removeBenchmark(item.benchmark_id)}><Trash2 size={16} />Delete</button>}
                  </td>
                </tr>
              ))}
              {!datasets.length && <tr><td colSpan="6">No benchmark datasets imported yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Benchmark Examples Preview {selectedDataset && <Badge value={selectedDataset.name} />}</h3></div>
        <div className="filter-row">
          <label>Split<select value={filters.split} onChange={(event) => updateFilter("split", event.target.value)}><option value="">All</option><option>train</option><option>validation</option><option>test</option><option>unsplit</option></select></label>
          <label>Label<select value={filters.label} onChange={(event) => updateFilter("label", event.target.value)}><option value="">All</option><option>contradiction</option><option>no_contradiction</option><option>uncertain</option></select></label>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Original ID</th><th>Type</th><th>Input preview</th><th>Target</th><th>Drift type</th><th>Severity</th><th>Split</th><th>Quality</th></tr></thead>
            <tbody>
              {examples.map((item) => (
                <tr key={item.example_id}>
                  <td className="mono-cell">{item.original_id}</td>
                  <td>{item.dataset_type}</td>
                  <td>{textPreview(item.input)}</td>
                  <td><Badge value={item.target?.label} /></td>
                  <td>{item.target?.drift_type}</td>
                  <td>{item.target?.severity}</td>
                  <td><Badge value={item.split} /></td>
                  <td><Badge value={Math.round(item.quality_score)} /></td>
                </tr>
              ))}
              {!examples.length && <tr><td colSpan="8">Select or upload a benchmark dataset to preview examples.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      {quality && (
        <section className="panel">
          <div className="section-heading"><h3>Quality Dashboard</h3></div>
          <div className="evaluation-grid benchmark-quality-grid">
            <div className="metric-card compact"><span>Total examples</span><strong>{quality.total_examples}</strong></div>
            <div className="metric-card compact"><span>Average quality score</span><strong>{quality.average_quality_score}</strong></div>
            <Distribution title="Labels" data={quality.label_distribution} />
            <Distribution title="Drift types" data={quality.drift_type_distribution} />
            <Distribution title="Severity" data={quality.severity_distribution} />
            <Distribution title="Splits" data={quality.split_distribution} />
          </div>
          <div className="agent-log">
            {(quality.warnings || []).map((item) => <div className="agent-log-row" key={item}><strong>Warning</strong><p>{item}</p></div>)}
            {(quality.recommendations || []).map((item) => <div className="agent-log-row" key={item}><strong>Recommendation</strong><p>{item}</p></div>)}
          </div>
        </section>
      )}

      <section className="panel">
        <div className="section-heading"><h3>Training Merge and Export</h3></div>
        <div className="filter-row">
          <label className="checkbox-label"><input type="checkbox" checked={mergeOptions.include_human_corrected} onChange={(event) => setMergeOptions({ ...mergeOptions, include_human_corrected: event.target.checked })} />Include human-corrected examples</label>
          <label>Max examples<input type="number" min="1" value={mergeOptions.max_examples} onChange={(event) => setMergeOptions({ ...mergeOptions, max_examples: event.target.value })} /></label>
          <button className="secondary-button" onClick={previewMerge}>Preview Merged Training Data</button>
          <label>Export name<input value={exportForm.name} onChange={(event) => setExportForm({ ...exportForm, name: event.target.value })} /></label>
          <label>Description<input value={exportForm.description} onChange={(event) => setExportForm({ ...exportForm, description: event.target.value })} /></label>
          <label>Format<select value={exportForm.format} onChange={(event) => setExportForm({ ...exportForm, format: event.target.value })}><option value="jsonl">jsonl</option><option value="json">json</option></select></label>
          <button className="primary-button" onClick={submitExport} disabled={!canManage}><Download size={16} />Export Training Dataset</button>
        </div>
        {mergeSummary && (
          <div className="evaluation-grid benchmark-quality-grid">
            <div className="metric-card compact"><span>Merged examples</span><strong>{mergeSummary.total_examples}</strong></div>
            <Distribution title="Dataset types" data={mergeSummary.dataset_type_distribution} />
            <Distribution title="Labels" data={mergeSummary.label_distribution} />
          </div>
        )}
      </section>

      <section className="panel">
        <div className="section-heading"><h3>Training Export History</h3></div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Format</th><th>Total</th><th>Train</th><th>Validation</th><th>Test</th><th>Created</th><th>Actions</th></tr></thead>
            <tbody>
              {exports.map((item) => (
                <tr key={item.export_id}>
                  <td>{item.name}</td>
                  <td><Badge value={item.format} /></td>
                  <td>{item.total_examples}</td>
                  <td>{item.train_count}</td>
                  <td>{item.validation_count}</td>
                  <td>{item.test_count}</td>
                  <td>{formatDate(item.created_at)}</td>
                  <td><button className="secondary-button" onClick={() => downloadTrainingExport(item.export_id, item.format)} disabled={!canManage}><Download size={16} />Download</button></td>
                </tr>
              ))}
              {!exports.length && <tr><td colSpan="8">No training exports created yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
