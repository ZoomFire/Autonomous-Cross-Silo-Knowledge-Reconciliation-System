import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import { exportLatestTimelineJson, exportLatestTimelineMarkdown } from "../api.js";

const entries = (value = {}) => Object.entries(value);

export default function TimelineDashboard({ report, onError }) {
  const [filters, setFilters] = useState({ source: "all", eventType: "all", severity: "all", driftType: "all" });

  const filteredCases = useMemo(() => {
    if (!report) return [];
    return report.cases
      .map((item) => ({
        ...item,
        events: item.events.filter((event) => {
          if (filters.source !== "all" && event.source !== filters.source) return false;
          if (filters.eventType !== "all" && event.event_type !== filters.eventType) return false;
          return true;
        }),
      }))
      .filter((item) => {
        if (filters.severity !== "all" && item.severity !== filters.severity) return false;
        if (filters.driftType !== "all" && item.drift_type !== filters.driftType) return false;
        return item.events.length > 0;
      });
  }, [report, filters]);

  if (!report) return null;

  const allEvents = report.cases.flatMap((item) => item.events);
  const unique = (items) => Array.from(new Set(items)).filter(Boolean);
  const update = (key, value) => setFilters({ ...filters, [key]: value });
  const exportReport = async (fn) => {
    try { await fn(); } catch (err) { onError(err.message); }
  };

  return (
    <section className="root-cause-stack">
      <div className="dashboard-grid">
        <div className="metric-card compact"><span>Total Cases</span><strong>{report.total_cases}</strong></div>
        <div className="metric-card compact"><span>Total Events</span><strong>{report.total_events}</strong></div>
        <div className="metric-card compact"><span>Cases With Drift</span><strong>{report.cases_with_drift}</strong></div>
      </div>
      <section className="panel insights-panel">
        <div className="section-heading"><h3>Timeline Summary</h3></div>
        <ul>{report.timeline_summary.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
      <section className="panel filters-panel">
        <div className="section-heading"><h3>Timeline Filters</h3></div>
        <div className="filters-grid">
          <label>Source<select value={filters.source} onChange={(event) => update("source", event.target.value)}><option value="all">All</option>{unique(allEvents.map((event) => event.source)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Event Type<select value={filters.eventType} onChange={(event) => update("eventType", event.target.value)}><option value="all">All</option>{unique(allEvents.map((event) => event.event_type)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Severity<select value={filters.severity} onChange={(event) => update("severity", event.target.value)}><option value="all">All</option>{unique(report.cases.map((item) => item.severity)).map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Drift Type<select value={filters.driftType} onChange={(event) => update("driftType", event.target.value)}><option value="all">All</option>{unique(report.cases.map((item) => item.drift_type)).map((item) => <option key={item}>{item}</option>)}</select></label>
        </div>
      </section>
      <section className="panel">
        <div className="section-heading"><h3>Case Timelines</h3></div>
        <div className="case-results">
          {filteredCases.map((item) => (
            <article className="case-detail" key={item.case_id}>
              <div className="case-detail-header"><strong>{item.case_id} - {item.title}</strong><span className={`badge ${item.severity.toLowerCase()}`}>{item.severity}</span></div>
              <p>{item.drift_type}</p>
              <div className="timeline-list">
                {item.events.map((event) => (
                  <div className="timeline-event" key={event.event_id}>
                    <span>{event.inferred_order}</span>
                    <div>
                      <div className="badge-row"><span className="badge info-badge">{event.source}</span><span className="badge neutral">{event.event_type}</span></div>
                      <strong>{event.title}</strong>
                      <p>{event.description}</p>
                      <em>Confidence: {event.confidence}</em>
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="panel export-panel">
        <div><h3>Export Timeline</h3><p>Download timeline report as JSON or Markdown.</p></div>
        <div className="control-actions">
          <button className="secondary-button" onClick={() => exportReport(exportLatestTimelineJson)}><Download size={17} />Export Timeline JSON</button>
          <button className="secondary-button" onClick={() => exportReport(exportLatestTimelineMarkdown)}><Download size={17} />Export Timeline Markdown</button>
        </div>
      </section>
    </section>
  );
}
