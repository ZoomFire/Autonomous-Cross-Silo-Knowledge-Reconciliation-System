export default function DriftReport({ report }) {
  return (
    <section className="panel report-panel">
      <div className="section-heading">
        <h3>Drift Report</h3>
        <span className={`badge ${report.severity.toLowerCase()}`}>{report.severity}</span>
      </div>
      <div className="report-grid">
        <div>
          <span>Drift ID</span>
          <strong>{report.drift_id}</strong>
        </div>
        <div>
          <span>Entity</span>
          <strong>{report.entity}</strong>
        </div>
        <div>
          <span>Drift Type</span>
          <strong>{report.drift_type}</strong>
        </div>
        <div>
          <span>Confidence Score</span>
          <strong>{Math.round(report.confidence_score * 100)}%</strong>
        </div>
        <div>
          <span>Recommended Action</span>
          <strong>{report.recommended_action}</strong>
        </div>
        <div>
          <span>Status</span>
          <strong>{report.status}</strong>
        </div>
      </div>
      <p className="report-summary">{report.summary}</p>
      <div className="evidence-list">
        <span>Evidence</span>
        {report.evidence.length === 0 ? (
          <p>No drift evidence found.</p>
        ) : (
          <ul>
            {report.evidence.map((item) => <li key={item}>{item}</li>)}
          </ul>
        )}
      </div>
    </section>
  );
}
