import { Gauge, Layers3, ShieldAlert, Target } from "lucide-react";

export default function DashboardCards({ claims, report }) {
  const driftDetected = report.drift_type !== "No Drift";
  const cards = [
    { label: "Total Claims", value: claims.length, icon: Layers3 },
    { label: "Drift Status", value: driftDetected ? "Drift Detected" : "No Drift", icon: Target },
    { label: "Severity", value: report.severity, icon: ShieldAlert, badge: report.severity },
    { label: "Confidence Score", value: `${Math.round(report.confidence_score * 100)}%`, icon: Gauge },
  ];

  return (
    <div className="dashboard-grid">
      {cards.map(({ label, value, icon: Icon, badge }) => (
        <div className="metric-card" key={label}>
          <div className="metric-icon"><Icon size={20} /></div>
          <span>{label}</span>
          <strong className={badge ? `severity-text ${badge.toLowerCase()}` : ""}>{value}</strong>
        </div>
      ))}
    </div>
  );
}
