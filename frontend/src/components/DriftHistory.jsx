import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { getReports } from "../api.js";

export default function DriftHistory() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadReports() {
    setLoading(true);
    setError("");
    try {
      setReports(await getReports());
    } catch {
      setError("Could not load reports. Please check backend server.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h2>Drift History</h2>
          <p>Saved SQLite reports sorted by newest first.</p>
        </div>
        <button className="secondary-button" onClick={loadReports} disabled={loading}>
          <RefreshCw size={17} />
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <section className="panel">
        {reports.length === 0 && !loading ? (
          <p className="empty-state">No analysis reports found yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Database ID</th>
                  <th>Drift ID</th>
                  <th>Entity</th>
                  <th>Drift Type</th>
                  <th>Severity</th>
                  <th>Confidence</th>
                  <th>Recommended Action</th>
                  <th>Status</th>
                  <th>Created At</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.id}>
                    <td>{report.id}</td>
                    <td>{report.drift_id}</td>
                    <td>{report.entity}</td>
                    <td>{report.drift_type}</td>
                    <td><span className={`badge ${report.severity.toLowerCase()}`}>{report.severity}</span></td>
                    <td>{Math.round(report.confidence_score * 100)}%</td>
                    <td>{report.recommended_action}</td>
                    <td>{report.status}</td>
                    <td>{new Date(report.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}
