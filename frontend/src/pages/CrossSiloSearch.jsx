import { Download, RefreshCw, Search, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { buildRagIndex, exportRagSearchMarkdown, getImportedSources, getRagChunks, getRagSearchHistory, getRagSearchHistoryItem, ragSearch } from "../api.js";
import HybridReasoningPanel from "../components/HybridReasoningPanel.jsx";
import { hasPermission } from "../components/PermissionGuard.jsx";

const SOURCE_TYPES = ["documentation", "code", "jira", "logs", "database_config", "commit"];

function Badge({ value }) {
  const className = value === "Critical" || value === true ? "failed" : value === "High" ? "warning" : value ? "success" : "neutral";
  return <span className={`badge ${className}`}>{String(value)}</span>;
}

export default function CrossSiloSearch({ user, workspaceId }) {
  const [query, setQuery] = useState("");
  const [sourceTypes, setSourceTypes] = useState(SOURCE_TYPES);
  const [topK, setTopK] = useState("8");
  const [answer, setAnswer] = useState(null);
  const [history, setHistory] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [sourceCount, setSourceCount] = useState(0);
  const [useHybridAnswer, setUseHybridAnswer] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const canIndex = hasPermission(user, "sync_connectors");
  const canViewChunks = hasPermission(user, "sync_connectors");

  async function loadHistory() {
    if (!workspaceId) return;
    const [historyItems, sourceItems] = await Promise.all([getRagSearchHistory(workspaceId), getImportedSources({})]);
    setHistory(historyItems);
    setSourceCount(sourceItems.length);
  }

  useEffect(() => {
    loadHistory().catch((err) => setError(err.message));
  }, [workspaceId]);

  async function runAction(label, fn) {
    setBusy(label);
    setError("");
    setMessage("");
    try {
      return await fn();
    } catch (err) {
      setError(err.message || "Action failed.");
      return null;
    } finally {
      setBusy("");
    }
  }

  async function handleIndex() {
    const result = await runAction("index", () => buildRagIndex(workspaceId));
    if (result) setMessage(`Search index rebuilt: ${result.chunks_created} chunks from ${result.sources_indexed} sources.`);
  }

  async function handleSearch() {
    const result = await runAction("search", () => ragSearch({ workspace_id: workspaceId, query, source_types: sourceTypes, top_k: Number(topK) }));
    if (result) {
      setAnswer(result);
      await loadHistory();
      if (!result.evidence?.length) setMessage("Search index is empty or no relevant chunks matched. Rebuild index first.");
    }
  }

  async function handleViewHistory(queryId) {
    const result = await runAction(`history-${queryId}`, () => getRagSearchHistoryItem(queryId));
    if (result) setAnswer(result.answer);
  }

  async function handleChunks() {
    const result = await runAction("chunks", () => getRagChunks({}));
    if (result) setChunks(result);
  }

  function toggleSourceType(type) {
    setSourceTypes((items) => (items.includes(type) ? items.filter((item) => item !== type) : [...items, type]));
  }

  return (
    <section className="page search-page">
      <div className="page-header">
        <div>
          <h2>Cross-Silo Semantic Search</h2>
          <p>Ask questions across imported documentation, code, tickets, logs, and configuration. DriftGuard retrieves evidence and highlights possible architectural drift.</p>
        </div>
      </div>

      {sourceCount === 0 && <div className="warning-box">No imported sources found. Please import sources from Connectors first.</div>}
      {message && <div className="success-banner">{message}</div>}
      {error && <div className="error-banner">{error}</div>}

      <div className="panel control-panel">
        <div className="section-heading">
          <h3><Sparkles size={18} /> Search Workspace Sources</h3>
          {canIndex && <button className="secondary-button" onClick={handleIndex} disabled={!workspaceId || busy === "index"}><RefreshCw size={16} />Rebuild Search Index</button>}
        </div>
        <div className="search-box-grid">
          <label className="wide-field">Ask a question<input placeholder="Why is refund API failing?" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
          <label>Top K<select value={topK} onChange={(event) => setTopK(event.target.value)}>{["5", "8", "10", "15"].map((value) => <option key={value}>{value}</option>)}</select></label>
          <button className="primary-button search-submit" onClick={handleSearch} disabled={!workspaceId || !query.trim() || busy === "search"}><Search size={16} />Search</button>
        </div>
        <div className="monitoring-checks">
          <label className="checkbox-label">
            <input type="checkbox" checked={useHybridAnswer} onChange={(event) => setUseHybridAnswer(event.target.checked)} />
            Use Hybrid Answer Generation
          </label>
          {SOURCE_TYPES.map((type) => (
            <label className="checkbox-label" key={type}>
              <input type="checkbox" checked={sourceTypes.includes(type)} onChange={() => toggleSourceType(type)} />
              {type}
            </label>
          ))}
        </div>
      </div>

      {answer && (
        <div className="results-stack">
          {useHybridAnswer && <HybridReasoningPanel taskType="rag_answer" inputContext={answer} workspaceId={workspaceId} />}
          <div className="panel answer-card">
            <div className="section-heading">
              <h3>Answer</h3>
              <div className="badge-row">
                <Badge value={`Confidence ${Math.round((answer.confidence_score || 0) * 100)}%`} />
                <Badge value={answer.severity_hint} />
                <Badge value={answer.possible_drift ? "Possible drift" : "No clear drift"} />
              </div>
            </div>
            <h3>{answer.short_answer}</h3>
            <p>{answer.evidence_summary}</p>
            <div className="report-grid">
              <div><span>Possible Drift</span><strong>{answer.possible_drift ? "Yes" : "No"}</strong></div>
              <div><span>Drift Type</span><strong>{answer.possible_drift_type}</strong></div>
              <div><span>Severity Hint</span><strong>{answer.severity_hint}</strong></div>
            </div>
            <div className="source-coverage">
              {Object.entries(answer.source_coverage || {}).map(([type, count]) => <span className="source-badge" key={type}>{type}: {count}</span>)}
            </div>
            <ol>
              {(answer.recommended_next_steps || []).map((step) => <li key={step}>{step}</li>)}
            </ol>
          </div>

          <div className="evidence-grid">
            {(answer.evidence || []).map((item, index) => (
              <article className="panel evidence-card" key={`${item.chunk_id}-${index}`}>
                <div className="section-heading">
                  <h3>{item.source_name}</h3>
                  <span className="badge info-badge">{item.source_type}</span>
                </div>
                <p>{item.chunk_text}</p>
                <div className="source-coverage">
                  <span className="source-badge">Score: {item.score}</span>
                  <span className="source-badge">Matched: {(item.matched_keywords || []).join(", ") || "none"}</span>
                </div>
                <pre className="json-preview">{JSON.stringify(item.metadata || {}, null, 2)}</pre>
              </article>
            ))}
          </div>
        </div>
      )}

      <div className="results-stack">
        <div className="panel">
          <div className="section-heading">
            <h3>Search History</h3>
            <button className="secondary-button" onClick={loadHistory}><RefreshCw size={16} />Refresh</button>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Query</th><th>Created</th><th>Confidence</th><th>Possible Drift</th><th>Severity</th><th>Actions</th></tr></thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.query_id}>
                    <td>{item.query_text}</td>
                    <td>{item.created_at}</td>
                    <td>{Math.round((item.answer?.confidence_score || 0) * 100)}%</td>
                    <td>{item.answer?.possible_drift ? "Yes" : "No"}</td>
                    <td>{item.answer?.severity_hint}</td>
                    <td><div className="row-actions"><button className="secondary-button" onClick={() => handleViewHistory(item.query_id)}>View</button><button className="secondary-button" onClick={() => exportRagSearchMarkdown(item.query_id)}><Download size={15} />Export</button></div></td>
                  </tr>
                ))}
                {!history.length && <tr><td colSpan="6" className="empty-state">No search history yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        {canViewChunks && (
          <div className="panel">
            <div className="section-heading">
              <h3>Indexed Chunks</h3>
              <button className="secondary-button" onClick={handleChunks}><Search size={16} />View Indexed Chunks</button>
            </div>
            {!!chunks.length && (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Source</th><th>Type</th><th>Tokens</th><th>Preview</th></tr></thead>
                  <tbody>{chunks.slice(0, 50).map((chunk) => <tr key={chunk.chunk_id}><td>{chunk.source_name}</td><td>{chunk.source_type}</td><td>{chunk.token_count}</td><td>{chunk.chunk_text.slice(0, 240)}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
