import { Database, FileUp, GitBranch, Play, RefreshCw, Search, Trash2, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  createConnector,
  deleteConnector,
  deleteImportedSource,
  generateDatasetFromConnector,
  generateDatasetFromSources,
  getConnectorSyncRuns,
  getConnectors,
  getImportedSource,
  getImportedSources,
  syncConnector,
  testConnector,
  uploadConnectorSources,
} from "../api.js";
import { hasPermission } from "../components/PermissionGuard.jsx";

const CONNECTOR_TYPES = ["jira", "confluence", "logs", "config", "manual_upload"];
const SOURCE_TYPES = ["", "documentation", "code", "jira", "logs", "database_config", "commit", "unknown"];

function Badge({ value }) {
  const className = value === "active" || value === "completed" ? "success" : value === "error" || value === "failed" ? "failed" : value === "partial" ? "warning" : "info";
  return <span className={`badge ${className}`}>{value || "unknown"}</span>;
}

function toInputList(value) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export default function ConnectorDashboard({ user, workspaceId }) {
  const [connectors, setConnectors] = useState([]);
  const [sources, setSources] = useState([]);
  const [syncRuns, setSyncRuns] = useState([]);
  const [selectedConnectorId, setSelectedConnectorId] = useState("");
  const [selectedSourceIds, setSelectedSourceIds] = useState([]);
  const [sourceDetail, setSourceDetail] = useState(null);
  const [filters, setFilters] = useState({ connector_id: "", source_type: "", search: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [githubForm, setGithubForm] = useState({
    name: "",
    repo_url: "",
    branch: "main",
    access_token: "",
    include_extensions: ".py,.js,.jsx,.ts,.tsx,.md,.json,.yaml,.yml,.env",
    exclude_dirs: "node_modules,.git,dist,build,__pycache__,venv,.venv,target,coverage",
  });
  const [uploadForm, setUploadForm] = useState({ name: "", connector_type: "jira", files: [] });
  const [datasetForm, setDatasetForm] = useState({ dataset_name: "Generated Dataset from Enterprise Sources", description: "Auto-generated dataset from imported enterprise sources", version: "1.0" });

  const canView = hasPermission(user, "view_connectors");
  const canManage = hasPermission(user, "manage_connectors");
  const canSync = hasPermission(user, "sync_connectors");
  const canGenerate = hasPermission(user, "generate_connector_datasets");
  const canDelete = user?.role === "admin" || user?.role === "engineer";

  const connectorById = useMemo(() => Object.fromEntries(connectors.map((connector) => [connector.connector_id, connector])), [connectors]);

  async function loadAll(nextFilters = filters) {
    if (!workspaceId || !canView) return;
    const [connectorItems, sourceItems] = await Promise.all([getConnectors(workspaceId), getImportedSources(nextFilters)]);
    setConnectors(connectorItems);
    setSources(sourceItems);
  }

  useEffect(() => {
    loadAll().catch((err) => setError(err.message));
  }, [workspaceId]);

  async function runAction(label, action) {
    setBusy(label);
    setError("");
    setMessage("");
    try {
      const result = await action();
      await loadAll();
      return result;
    } catch (err) {
      setError(err.message || "Action failed.");
      return null;
    } finally {
      setBusy("");
    }
  }

  async function handleCreateGitHub() {
    const created = await runAction("create-github", () => createConnector({
      name: githubForm.name || "GitHub Repository",
      connector_type: "github",
      config: {
        repo_url: githubForm.repo_url,
        branch: githubForm.branch || "main",
        access_token: githubForm.access_token,
        include_extensions: toInputList(githubForm.include_extensions),
        exclude_dirs: toInputList(githubForm.exclude_dirs),
      },
    }));
    if (created) {
      setSelectedConnectorId(created.connector_id);
      setMessage("GitHub connector created.");
    }
  }

  async function handleTest(connectorId) {
    const result = await runAction(`test-${connectorId}`, () => testConnector(connectorId));
    if (result) setMessage(result.message || "Connector test completed.");
  }

  async function handleSync(connectorId) {
    const result = await runAction(`sync-${connectorId}`, () => syncConnector(connectorId));
    if (result) {
      setMessage(`Sync completed. Imported ${result.imported_sources?.length || 0} source(s).`);
      await loadSyncRuns(connectorId);
    }
  }

  async function handleUpload() {
    const formData = new FormData();
    formData.append("workspace_id", workspaceId);
    formData.append("connector_type", uploadForm.connector_type);
    formData.append("name", uploadForm.name || "Uploaded Sources");
    Array.from(uploadForm.files).forEach((file) => formData.append("files", file));
    const result = await runAction("upload", () => uploadConnectorSources(formData));
    if (result) setMessage(`Imported ${result.imported_sources?.length || 0} uploaded source(s).`);
  }

  async function loadSyncRuns(connectorId) {
    setSelectedConnectorId(connectorId);
    const runs = await getConnectorSyncRuns(connectorId);
    setSyncRuns(runs);
  }

  async function openSource(sourceId) {
    const detail = await runAction(`source-${sourceId}`, () => getImportedSource(sourceId));
    if (detail) setSourceDetail(detail);
  }

  async function handleDeleteConnector(connectorId) {
    const result = await runAction(`delete-connector-${connectorId}`, () => deleteConnector(connectorId));
    if (result) setMessage("Connector deleted.");
  }

  async function handleDeleteSource(sourceId) {
    const result = await runAction(`delete-source-${sourceId}`, () => deleteImportedSource(sourceId));
    if (result) {
      setSelectedSourceIds((ids) => ids.filter((id) => id !== sourceId));
      setMessage("Imported source deleted.");
    }
  }

  async function handleGenerateSelected() {
    const result = await runAction("generate-selected", () => generateDatasetFromSources({ ...datasetForm, workspace_id: workspaceId, source_ids: selectedSourceIds }));
    if (result) setMessage("Dataset generated and saved to Dataset Library.");
  }

  async function handleGenerateConnector(connectorId) {
    const result = await runAction(`generate-${connectorId}`, () => generateDatasetFromConnector(connectorId, datasetForm));
    if (result) setMessage("Dataset generated and saved to Dataset Library.");
  }

  function toggleSource(sourceId) {
    setSelectedSourceIds((ids) => (ids.includes(sourceId) ? ids.filter((id) => id !== sourceId) : [...ids, sourceId]));
  }

  if (!canView) {
    return <section className="page"><div className="error-banner">You do not have permission to view connectors.</div></section>;
  }

  return (
    <section className="page connector-page">
      <div className="page-header">
        <div>
          <h2>Enterprise Source Connectors</h2>
          <p>Import documentation, code, tickets, logs, and configuration from real project sources, then generate DriftGuard evaluation datasets.</p>
        </div>
      </div>

      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <div className="connector-grid">
        <div className="panel control-panel">
          <div className="section-heading">
            <h3><GitBranch size={18} /> GitHub Repository Import</h3>
          </div>
          <div className="connector-form-grid">
            <label>Connector name<input value={githubForm.name} onChange={(event) => setGithubForm({ ...githubForm, name: event.target.value })} disabled={!canManage} /></label>
            <label>GitHub repository URL<input value={githubForm.repo_url} onChange={(event) => setGithubForm({ ...githubForm, repo_url: event.target.value })} disabled={!canManage} /></label>
            <label>Branch<input value={githubForm.branch} onChange={(event) => setGithubForm({ ...githubForm, branch: event.target.value })} disabled={!canManage} /></label>
            <label>Access token optional<input type="password" value={githubForm.access_token} onChange={(event) => setGithubForm({ ...githubForm, access_token: event.target.value })} disabled={!canManage} /></label>
            <label className="wide-field">Include extensions<input value={githubForm.include_extensions} onChange={(event) => setGithubForm({ ...githubForm, include_extensions: event.target.value })} disabled={!canManage} /></label>
            <label className="wide-field">Exclude directories<input value={githubForm.exclude_dirs} onChange={(event) => setGithubForm({ ...githubForm, exclude_dirs: event.target.value })} disabled={!canManage} /></label>
          </div>
          <div className="control-actions">
            <button className="primary-button" onClick={handleCreateGitHub} disabled={!canManage || busy === "create-github"}><Database size={16} />Create Connector</button>
            <button className="secondary-button" onClick={() => selectedConnectorId && handleTest(selectedConnectorId)} disabled={!canSync || !selectedConnectorId}><Play size={16} />Test Connection</button>
            <button className="secondary-button" onClick={() => selectedConnectorId && handleSync(selectedConnectorId)} disabled={!canSync || !selectedConnectorId}><RefreshCw size={16} />Sync Repository</button>
          </div>
        </div>

        <div className="panel control-panel">
          <div className="section-heading">
            <h3><FileUp size={18} /> Upload Source Files</h3>
          </div>
          <div className="connector-form-grid">
            <label>Connector/source name<input value={uploadForm.name} onChange={(event) => setUploadForm({ ...uploadForm, name: event.target.value })} disabled={!canSync} /></label>
            <label>Connector type<select value={uploadForm.connector_type} onChange={(event) => setUploadForm({ ...uploadForm, connector_type: event.target.value })} disabled={!canSync}>{CONNECTOR_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}</select></label>
            <label className="file-upload wide-field"><FileUp size={18} /><span>{uploadForm.files?.length ? `${uploadForm.files.length} file(s) selected` : "Choose source files"}</span><input type="file" multiple onChange={(event) => setUploadForm({ ...uploadForm, files: event.target.files })} disabled={!canSync} /></label>
          </div>
          <button className="primary-button" onClick={handleUpload} disabled={!canSync || !uploadForm.files?.length || busy === "upload"}><FileUp size={16} />Upload and Import Sources</button>
        </div>
      </div>

      <div className="results-stack">
        <div className="panel">
          <div className="section-heading">
            <h3>Connector List</h3>
            <button className="secondary-button" onClick={() => loadAll()}><RefreshCw size={16} />Refresh</button>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Last sync</th><th>Created</th><th>Actions</th></tr></thead>
              <tbody>
                {connectors.map((connector) => (
                  <tr key={connector.connector_id}>
                    <td><strong>{connector.name}</strong></td>
                    <td>{connector.connector_type}</td>
                    <td><Badge value={connector.status} /></td>
                    <td>{connector.last_sync_at || "Never"}</td>
                    <td>{connector.created_at}</td>
                    <td>
                      <div className="row-actions">
                        <button className="secondary-button" onClick={() => handleTest(connector.connector_id)} disabled={!canSync}>Test</button>
                        <button className="secondary-button" onClick={() => handleSync(connector.connector_id)} disabled={!canSync || connector.connector_type !== "github"}>Sync</button>
                        <button className="secondary-button" onClick={() => setFilters({ ...filters, connector_id: connector.connector_id })}>View Sources</button>
                        <button className="secondary-button" onClick={() => loadSyncRuns(connector.connector_id)}>Sync History</button>
                        <button className="secondary-button" onClick={() => handleGenerateConnector(connector.connector_id)} disabled={!canGenerate}><Wand2 size={15} />Generate</button>
                        {canDelete && <button className="secondary-button danger-button" onClick={() => handleDeleteConnector(connector.connector_id)}><Trash2 size={15} />Delete</button>}
                      </div>
                    </td>
                  </tr>
                ))}
                {!connectors.length && <tr><td colSpan="6" className="empty-state">No connectors found.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <div className="section-heading">
            <h3>Imported Source Library</h3>
          </div>
          <div className="filters-grid">
            <label>Source type<select value={filters.source_type} onChange={(event) => setFilters({ ...filters, source_type: event.target.value })}>{SOURCE_TYPES.map((type) => <option key={type || "all"} value={type}>{type || "all"}</option>)}</select></label>
            <label>Connector<select value={filters.connector_id} onChange={(event) => setFilters({ ...filters, connector_id: event.target.value })}><option value="">all</option>{connectors.map((connector) => <option key={connector.connector_id} value={connector.connector_id}>{connector.name}</option>)}</select></label>
            <label>Search<input value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} /></label>
            <button className="secondary-button filter-button" onClick={() => loadAll(filters)}><Search size={16} />Apply Filters</button>
          </div>
          <div className="source-list">
            {sources.map((source) => (
              <article className="source-card" key={source.source_id}>
                <label className="checkbox-label"><input type="checkbox" checked={selectedSourceIds.includes(source.source_id)} onChange={() => toggleSource(source.source_id)} />Select</label>
                <div>
                  <strong>{source.source_name}</strong>
                  <p>{source.source_path}</p>
                  <p>{source.content_preview}</p>
                </div>
                <div className="badge-row">
                  <span className="badge info-badge">{source.source_type}</span>
                  <span className="badge neutral">{connectorById[source.connector_id]?.name || "connector"}</span>
                </div>
                <div className="row-actions">
                  <button className="secondary-button" onClick={() => openSource(source.source_id)}>View</button>
                  {canDelete && <button className="secondary-button danger-button" onClick={() => handleDeleteSource(source.source_id)}>Delete</button>}
                </div>
              </article>
            ))}
            {!sources.length && <p className="empty-state">No imported sources found.</p>}
          </div>
        </div>

        {sourceDetail && (
          <div className="panel">
            <div className="section-heading">
              <h3>Source Detail</h3>
              <button className="secondary-button" onClick={() => setSourceDetail(null)}>Close</button>
            </div>
            <div className="report-grid">
              <div><span>Name</span><strong>{sourceDetail.source_name}</strong></div>
              <div><span>Type</span><strong>{sourceDetail.source_type}</strong></div>
              <div><span>Path</span><strong>{sourceDetail.source_path || "n/a"}</strong></div>
            </div>
            <pre className="json-preview">{JSON.stringify({ url: sourceDetail.source_url, metadata: sourceDetail.metadata }, null, 2)}</pre>
            <pre className="json-preview">{sourceDetail.content_text}</pre>
          </div>
        )}

        <div className="panel">
          <div className="section-heading">
            <h3>Generate Dataset</h3>
            <span className="source-strip">{selectedSourceIds.length} selected source(s)</span>
          </div>
          <div className="save-grid">
            <label>Dataset name<input value={datasetForm.dataset_name} onChange={(event) => setDatasetForm({ ...datasetForm, dataset_name: event.target.value })} /></label>
            <label>Description<input value={datasetForm.description} onChange={(event) => setDatasetForm({ ...datasetForm, description: event.target.value })} /></label>
            <label>Version<input value={datasetForm.version} onChange={(event) => setDatasetForm({ ...datasetForm, version: event.target.value })} /></label>
            <button className="primary-button" onClick={handleGenerateSelected} disabled={!canGenerate || !selectedSourceIds.length}><Wand2 size={16} />Generate Dataset from Selected Sources</button>
          </div>
        </div>

        <div className="panel">
          <div className="section-heading">
            <h3>Sync History</h3>
            <span className="source-strip">{selectedConnectorId ? connectorById[selectedConnectorId]?.name : "No connector selected"}</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Sync ID</th><th>Type</th><th>Status</th><th>Started</th><th>Completed</th><th>Imported</th><th>Skipped</th><th>Summary</th></tr></thead>
              <tbody>
                {syncRuns.map((run) => (
                  <tr key={run.sync_id}>
                    <td>{run.sync_id.slice(0, 8)}</td>
                    <td>{run.connector_type}</td>
                    <td><Badge value={run.status} /></td>
                    <td>{run.started_at}</td>
                    <td>{run.completed_at}</td>
                    <td>{run.files_imported}</td>
                    <td>{run.files_skipped}</td>
                    <td>{run.summary}{run.errors?.length ? ` (${run.errors.length} error(s))` : ""}</td>
                  </tr>
                ))}
                {!syncRuns.length && <tr><td colSpan="8" className="empty-state">No sync runs selected.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
