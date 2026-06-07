import { useEffect, useState } from "react";
import { DatabaseBackup, Upload } from "lucide-react";
import {
  downloadDatabaseBackup,
  getDatabaseHealth,
  getDatabaseIntegrity,
  migrateJsonToDatabase,
  restoreDatabaseBackup,
} from "../api.js";
import PermissionGuard from "../components/PermissionGuard.jsx";

function StatusBadge({ value }) {
  return <span className={`badge ${value === "healthy" || value === "clean" ? "success" : "failed"}`}>{value}</span>;
}

export default function SystemAdminDashboard({ user }) {
  const [health, setHealth] = useState(null);
  const [integrity, setIntegrity] = useState(null);
  const [migration, setMigration] = useState(null);
  const [restoreResult, setRestoreResult] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState("");

  async function loadHealth() {
    try {
      setHealth(await getDatabaseHealth());
    } catch (err) {
      setError(err.message || "Database health check failed.");
    }
  }

  async function runIntegrity() {
    try {
      setIntegrity(await getDatabaseIntegrity());
    } catch (err) {
      setError(err.message || "Integrity check failed.");
    }
  }

  useEffect(() => {
    loadHealth();
    runIntegrity();
  }, []);

  async function runMigration() {
    setError("");
    try {
      setMigration(await migrateJsonToDatabase());
      await loadHealth();
      await runIntegrity();
    } catch (err) {
      setError(err.message || "Migration failed.");
    }
  }

  async function restoreBackup() {
    if (!selectedFile) {
      setError("Please select a backup JSON file.");
      return;
    }
    if (!confirm("Restoring backup may overwrite existing data. Are you sure?")) return;
    setError("");
    try {
      setRestoreResult(await restoreDatabaseBackup(selectedFile));
      await loadHealth();
      await runIntegrity();
    } catch (err) {
      setError(err.message || "Restore failed.");
    }
  }

  const tableCounts = health?.tables || {};

  return (
    <PermissionGuard user={user} permission="manage_users" fallback={<section className="page"><div className="error-banner">Permission denied. System Admin is available only for admins.</div></section>}>
      <section className="page">
        <div className="page-header">
          <div>
            <h2>System Admin</h2>
            <p>Database persistence, migration, backup, restore, and integrity validation.</p>
          </div>
        </div>

        <section className="info-box">
          <strong>System Database and Storage</strong><br />
          Manage DriftGuard AI local database, migrate JSON storage, create backups, restore backups, and validate data integrity.
        </section>
        {error && <div className="error-banner">{error}</div>}

        {health && (
          <div className="dashboard-grid">
            <div className="metric-card compact"><span>Database Enabled</span><strong>{String(health.database_enabled)}</strong></div>
            <div className="metric-card compact"><span>Database Type</span><strong>{health.database_type}</strong></div>
            <div className="metric-card compact"><span>Status</span><strong><StatusBadge value={health.status} /></strong></div>
            <div className="metric-card compact"><span>Users</span><strong>{tableCounts.users || 0}</strong></div>
            <div className="metric-card compact"><span>Workspaces</span><strong>{tableCounts.workspaces || 0}</strong></div>
            <div className="metric-card compact"><span>Datasets</span><strong>{tableCounts.datasets || 0}</strong></div>
            <div className="metric-card compact"><span>Evaluations</span><strong>{tableCounts.evaluations || 0}</strong></div>
            <div className="metric-card compact"><span>Feedback</span><strong>{tableCounts.feedback || 0}</strong></div>
            <div className="metric-card compact"><span>Alerts</span><strong>{tableCounts.alerts || 0}</strong></div>
            <div className="metric-card compact"><span>Audit Events</span><strong>{tableCounts.audit_events || 0}</strong></div>
          </div>
        )}

        <section className="panel export-panel">
          <div>
            <h3>JSON Migration</h3>
            <p>Migrate existing local JSON storage into SQLite. Existing JSON files are kept for backward compatibility.</p>
          </div>
          <button className="primary-button" onClick={runMigration}>Migrate JSON Storage to Database</button>
        </section>
        {migration && <section className="panel"><pre className="json-preview">{JSON.stringify(migration, null, 2)}</pre></section>}

        <section className="panel export-panel">
          <div>
            <h3>Backup and Restore</h3>
            <p>Create a portable JSON backup or restore a validated Level 3.0 backup file.</p>
          </div>
          <div className="control-actions">
            <button className="secondary-button" onClick={downloadDatabaseBackup}><DatabaseBackup size={17} />Download Database Backup</button>
            <label className="file-upload">
              <Upload size={17} />
              <span>{selectedFile ? selectedFile.name : "Restore Backup JSON"}</span>
              <input type="file" accept=".json,application/json" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} />
            </label>
            <button className="primary-button" onClick={restoreBackup}>Restore Backup</button>
          </div>
        </section>
        {restoreResult && <section className="panel"><pre className="json-preview">{JSON.stringify(restoreResult, null, 2)}</pre></section>}

        <section className={integrity?.issues_found ? "panel warning-panel" : "panel"}>
          <div className="section-heading">
            <h3>Data Integrity</h3>
            {integrity && <StatusBadge value={integrity.status} />}
          </div>
          <button className="secondary-button" onClick={runIntegrity}>Run Data Integrity Check</button>
          {integrity && (
            <pre className="json-preview">{JSON.stringify(integrity, null, 2)}</pre>
          )}
        </section>
      </section>
    </PermissionGuard>
  );
}
