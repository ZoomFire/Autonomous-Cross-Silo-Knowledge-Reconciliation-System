# DriftGuard AI: Autonomous Cross-Silo Knowledge Reconciliation System

Level 4.7 is a full-stack MVP for manually detecting architectural drift, evaluating rule accuracy, managing benchmark datasets, importing real enterprise sources through connectors, searching across imported sources with local RAG-style evidence retrieval, collecting human corrections, generating root-cause recommendations, visualizing drift timelines and impact graphs, proactively monitoring saved datasets for drift alerts, protecting the app with local authentication, workspaces, roles, permissions, recording enterprise audit/compliance events, importing public benchmark datasets, preparing training data exports, training lightweight local baseline models, comparing model experiments, deploying selected local models, managing drift incidents with comments/timelines/webhooks/escalation rules, syncing incidents into external workflow integrations, generating executive ROI reports, running guided demo mode, running end-to-end validation and research result reports, and persisting production-style data in SQLite.

## Features

- Manual input for documentation, code, Jira, commits, logs, and database config
- Regex entity extraction for API endpoints
- Rule-based claim extraction and claim validation
- Truth Triangle grouping across requirement, implementation, and runtime views
- Drift detection with severity, confidence, evidence, and recommended actions
- Dataset Evaluation for contradiction, no-drift, and manual-review cases
- Custom JSON dataset upload, preview, and evaluation
- Dataset quality validation, confusion matrices, summary insights, and exportable reports
- Local benchmark dataset library and evaluation history tracking
- Human feedback, corrected dataset export, and training dataset builder
- Root cause analysis, owner suggestion, priority scoring, and action plans
- Architecture drift timeline and impact graph analysis
- Proactive monitoring rules, manual monitoring runs, alert status tracking, and alert exports
- Incident Management dashboard with severity/status queues, assignment, comments, timeline events, markdown export, webhooks, notification logs, and escalation rules
- External workflow integrations for Jira-style tickets, GitHub Issues, Slack/Teams-style notifications, generic webhooks, mock external items, sync records, and linked resources
- Executive dashboard with drift risk, incident, model health, compliance, integration activity, ROI estimates, report export, and enterprise demo mode
- Validation and research dashboard with real/demo validation runs, baseline comparison, ablation studies, chart data, research reports, and JSON/CSV/Markdown exports
- Local signup, login, logout, session tokens, user profiles, workspaces, and role-based permissions
- Enterprise audit trail, security event tracking, compliance risk summaries, and audit exports
- Enterprise source connectors for GitHub repositories, Jira-style exports, Confluence-style docs, logs, config files, and manual uploads
- Imported source library, source normalization, connector sync history, and generated dataset cases
- Local RAG-style cross-silo search over imported documentation, code, Jira, logs, and config
- Evidence cards, source coverage, search history, drift hints, and Markdown export for search answers
- SQLite database persistence, JSON migration, database backup/restore, health checks, and integrity validation
- Dashboard-style React UI
- SQLite storage and report history

## Tech Stack

- Backend: FastAPI, Pydantic, SQLite, rule-based Python logic
- Frontend: React, Vite, plain CSS
- APIs: Local HTTP only, no paid APIs or external keys

## Folder Structure

```text
backend/
  main.py
  models.py
  claim_extractor.py
  drift_detector.py
  dataset_evaluator.py
  dataset_store.py
  feedback_store.py
  root_cause_analyzer.py
  drift_timeline.py
  impact_graph.py
  monitoring_store.py
  auth_store.py
  workspace_store.py
  permissions.py
  audit_store.py
  config.py
  database/
    __init__.py
    db.py
    models.py
    repositories.py
    migrate_json_to_db.py
    backup_restore.py
  sample_dataset.json
  storage/
    auth/
      users/
      sessions/
    audit/
    driftguard.db
    datasets/
    evaluations/
    feedback/
    workspaces/
    monitoring/
      rules/
      runs/
      alerts/
  database.py
  requirements.txt
frontend/
  package.json
  index.html
  src/
    main.jsx
    App.jsx
    api.js
    components/
    styles.css
README.md
```

## Backend Setup

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

For macOS/Linux:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## API Endpoints

- `GET /health` returns backend service status
- `POST /analyze` extracts claims, builds the Truth Triangle, detects drift, saves a report, and returns the analysis
- `GET /reports` returns saved reports sorted newest first
- `GET /reports/{report_id}` returns one saved report
- `GET /dataset/sample` returns the local benchmark dataset
- `POST /dataset/evaluate` evaluates all sample cases and returns accuracy metrics
- `POST /dataset/upload-preview` validates and previews an uploaded JSON dataset
- `POST /dataset/upload-evaluate` evaluates an uploaded JSON dataset
- `GET /dataset/evaluation/latest/export-json` downloads the latest evaluation as JSON
- `GET /dataset/evaluation/latest/export-markdown` downloads the latest evaluation as Markdown
- `POST /dataset/save-uploaded` saves an uploaded dataset locally
- `GET /dataset/library` lists saved dataset metadata
- `GET /dataset/library/{dataset_id}` returns a saved dataset with cases
- `DELETE /dataset/library/{dataset_id}` deletes a saved dataset
- `POST /dataset/library/{dataset_id}/evaluate` evaluates a saved dataset
- `GET /dataset/evaluations/history` lists saved evaluation runs
- `GET /dataset/evaluations/history/{evaluation_id}` returns one saved evaluation
- `DELETE /dataset/evaluations/history/{evaluation_id}` deletes one saved evaluation
- `GET /dataset/evaluations/compare?base_id=...&current_id=...` compares two evaluation runs
- `POST /feedback/case` saves or updates human feedback for one evaluated case
- `GET /feedback` lists all feedback
- `GET /feedback/evaluation/{evaluation_id}` lists feedback for an evaluation
- `GET /feedback/evaluation/{evaluation_id}/summary` returns review progress and correction stats
- `DELETE /feedback/{feedback_id}` deletes feedback
- `GET /feedback/evaluation/{evaluation_id}/export-corrected-dataset` downloads corrected cases
- `GET /feedback/evaluation/{evaluation_id}/build-training-dataset` downloads training-ready items
- `GET /root-cause/latest` analyzes the latest evaluation
- `GET /root-cause/evaluation/{evaluation_id}` analyzes an evaluation history item
- `GET /root-cause/latest/export-json` exports the latest root cause report as JSON
- `GET /root-cause/latest/export-markdown` exports the latest root cause report as Markdown
- `GET /timeline/latest` generates a timeline for the latest evaluation
- `GET /timeline/evaluation/{evaluation_id}` generates a timeline for a saved evaluation
- `GET /timeline/latest/export-json` exports the latest timeline as JSON
- `GET /timeline/latest/export-markdown` exports the latest timeline as Markdown
- `GET /impact-graph/latest` generates an impact graph for the latest evaluation
- `GET /impact-graph/evaluation/{evaluation_id}` generates an impact graph for a saved evaluation
- `GET /impact-graph/latest/export-json` exports the latest impact graph as JSON
- `POST /monitoring/rules` creates a monitoring rule for a saved dataset
- `GET /monitoring/rules` lists monitoring rules
- `GET /monitoring/rules/{rule_id}` returns one monitoring rule
- `PUT /monitoring/rules/{rule_id}` updates one monitoring rule
- `DELETE /monitoring/rules/{rule_id}` deletes one monitoring rule
- `POST /monitoring/rules/{rule_id}/run` runs a monitoring check
- `GET /monitoring/runs` lists monitoring runs
- `GET /monitoring/runs/{run_id}` returns one monitoring run
- `DELETE /monitoring/runs/{run_id}` deletes one monitoring run
- `GET /monitoring/alerts` lists monitoring alerts
- `GET /monitoring/alerts/export-json` downloads alerts as JSON
- `GET /monitoring/alerts/export-markdown` downloads alerts as Markdown
- `GET /monitoring/alerts/{alert_id}` returns one monitoring alert
- `PUT /monitoring/alerts/{alert_id}/status` updates alert status to `open`, `acknowledged`, or `resolved`
- `DELETE /monitoring/alerts/{alert_id}` deletes one monitoring alert
- `POST /incidents` creates a drift incident
- `POST /incidents/from-alert` creates an incident from a monitoring alert
- `GET /incidents` lists incidents with optional status/severity/source/owner filters
- `GET /incidents/summary` returns incident counts and incident automation config
- `GET /incidents/{incident_id}` returns incident detail, comments, and timeline
- `PUT /incidents/{incident_id}/status` updates incident status
- `PUT /incidents/{incident_id}/assign` updates incident owner
- `POST /incidents/{incident_id}/comments` adds an incident comment
- `DELETE /incidents/{incident_id}` deletes an incident for admins
- `GET /incidents/{incident_id}/export-markdown` downloads an incident report
- `POST /incidents/webhooks` creates an incident webhook
- `GET /incidents/webhooks` lists incident webhooks
- `PUT /incidents/webhooks/{webhook_id}` updates a webhook
- `DELETE /incidents/webhooks/{webhook_id}` deletes a webhook
- `POST /incidents/webhooks/{webhook_id}/test` sends a test webhook event
- `GET /incidents/notification-logs` lists webhook delivery attempts
- `POST /incidents/escalation-rules` creates an escalation rule
- `GET /incidents/escalation-rules` lists escalation rules
- `PUT /incidents/escalation-rules/{rule_id}` updates an escalation rule
- `DELETE /incidents/escalation-rules/{rule_id}` deletes an escalation rule
- `POST /incidents/escalations/check` runs escalation checks
- `POST /integrations` creates an external workflow integration
- `GET /integrations` lists integrations
- `GET /integrations/{integration_id}` returns one integration with masked config
- `PUT /integrations/{integration_id}` updates one integration
- `DELETE /integrations/{integration_id}` deletes one integration for admins
- `POST /integrations/{integration_id}/test` tests integration health
- `POST /integrations/{integration_id}/incident/{incident_id}/sync` syncs an incident to an external ticket, issue, or message
- `POST /integrations/{integration_id}/incident/{incident_id}/notify` sends an external incident notification
- `GET /integrations/sync-records` lists external sync records
- `GET /integrations/linked-resources` lists linked external resources
- `GET /integrations/health-summary` returns integration health metrics
- `GET /integrations/mock-items` lists locally simulated external tickets/issues/messages
- `GET /executive/metrics` returns executive KPI and risk metrics
- `POST /executive/roi` calculates ROI from configurable assumptions
- `POST /executive/report` generates and stores an executive report
- `GET /executive/reports` lists executive reports
- `GET /executive/reports/{report_id}` returns one executive report
- `GET /executive/reports/{report_id}/export-markdown` exports an executive report
- `GET /demo/scenarios` lists guided demo scenarios
- `POST /demo/enable` enables demo mode
- `POST /demo/disable` disables demo mode
- `GET /demo/state` returns demo mode state
- `POST /demo/advance-step` advances the current demo walkthrough
- `POST /demo/reset` resets demo state for admins
- `POST /demo/seed-executive-demo` seeds safe executive demo data
- `POST /validation/run-real-dataset` runs real dataset validation
- `POST /validation/run-full-system` runs full system validation
- `POST /validation/run-demo-scenario` runs demo scenario validation
- `GET /validation/runs` lists validation runs
- `GET /validation/runs/{validation_id}` returns validation detail
- `DELETE /validation/runs/{validation_id}` deletes a validation run for admins
- `POST /validation/runs/{validation_id}/research-report` generates a research result
- `GET /validation/runs/{validation_id}/research-report/export-markdown` exports research markdown
- `GET /validation/runs/{validation_id}/export-json` exports validation JSON
- `GET /validation/runs/{validation_id}/export-csv` exports validation metrics CSV
- `POST /validation/baseline-comparison` compares rule-based/ML/hybrid baselines
- `POST /validation/ablation-study` runs MVP ablation study
- `GET /validation/demo-readiness` checks final demo readiness
- `GET /validation/research-results` lists research results
- `POST /auth/signup` creates the first admin or lets an admin create users
- `POST /auth/login` returns a local session token
- `POST /auth/logout` deletes the current session
- `GET /auth/me` returns the current user profile
- `GET /auth/users` lists users for admins
- `PUT /auth/users/{user_id}/role` updates a user role for admins
- `DELETE /auth/users/{user_id}` deletes a user for admins
- `POST /workspaces` creates a workspace
- `GET /workspaces` lists workspaces for the current user
- `GET /workspaces/{workspace_id}` returns one workspace
- `PUT /workspaces/{workspace_id}` updates a workspace
- `DELETE /workspaces/{workspace_id}` deletes a workspace
- `POST /workspaces/{workspace_id}/members` adds a user to a workspace
- `DELETE /workspaces/{workspace_id}/members/{user_id}` removes a workspace member
- `GET /workspaces/{workspace_id}/members` lists workspace members
- `GET /audit/events` lists audit events with optional filters
- `GET /audit/events/{audit_id}` returns one audit event
- `GET /audit/summary` returns audit summary metrics
- `GET /audit/compliance-risk` returns compliance risk scoring
- `GET /audit/export-json` downloads audit report JSON
- `GET /audit/export-markdown` downloads audit report Markdown
- `DELETE /audit/events/{audit_id}` deletes one audit event
- `GET /system/database/health` returns SQLite status and table counts
- `POST /system/database/migrate-json` migrates local JSON storage into SQLite
- `GET /system/database/backup` downloads a database backup JSON file
- `POST /system/database/restore` restores a database backup JSON file
- `GET /system/database/integrity` returns data integrity validation results

## Level 2: Dataset Evaluation

The project now includes a local JSON benchmark dataset in `backend/sample_dataset.json`.

The dataset contains:

- Contradiction cases
- No-drift match cases
- Manual-review weak evidence cases

The cases are inspired by:

- SNLI for contradiction and entailment-style reasoning
- CosQA for documentation/code alignment
- CommitPack for commit message and code-change reasoning
- Spider for database/config verification

The evaluator checks predicted label, drift type, and severity. It also supports compatible drift-type mappings when two labels are reasonably close, such as Documentation Drift and Configuration Drift for docs-vs-database conflicts.

Expected example for the included 20 sample cases:

- Total Cases: `20`
- Passed: depends on rule accuracy
- Failed: depends on rule accuracy
- Accuracy: calculated percentage

## Level 2.1: Real Dataset Upload

The system now supports uploading custom JSON datasets for evaluation. Users can preview and evaluate their own benchmark cases from the Dataset Evaluation page.

Supported dataset format:

```json
[
  {
    "case_id": "REAL-001",
    "title": "Public docs but internal code",
    "documentation": "...",
    "code": "...",
    "jira": "...",
    "commit": "...",
    "logs": "...",
    "database_config": "...",
    "expected_label": "contradiction",
    "expected_drift_type": "Documentation Drift",
    "expected_severity": "Critical"
  }
]
```

Only JSON array files are supported in Level 2.1. CSV support can be added in the next level.

## Level 2.2: Advanced Dataset Evaluation

The Dataset Evaluation page now includes:

- Dataset quality validation
- Confusion matrix tables
- Accuracy breakdown for labels, drift types, and severity
- Per-case mismatch explanations
- Summary insights
- Frontend filtering for correct, incorrect, severity, drift type, and label
- Export evaluation report as JSON
- Export evaluation report as Markdown

## Level 2.3: Benchmark Dataset Library and Evaluation History

DriftGuard AI now supports saving uploaded benchmark datasets locally, managing dataset versions, re-running evaluations, storing evaluation history, comparing evaluation runs, and detecting regressions.

Local JSON storage folders:

```text
backend/storage/datasets/
backend/storage/evaluations/
```

This level uses local JSON file storage only. A real database like PostgreSQL can be added in a future production level.

Testing flow:

1. Start backend:

```powershell
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

2. Start frontend:

```powershell
cd frontend
npm run dev
```

3. Open Dataset Evaluation.
4. Upload a JSON dataset.
5. Enter dataset name and version.
6. Click `Save Uploaded Dataset`.
7. Confirm it appears in Saved Dataset Library.
8. Click `View`.
9. Click `Evaluate`.
10. Confirm the run appears in Evaluation History.
11. Run another evaluation.
12. Compare two evaluations.
13. Check regression detection.
14. Delete a dataset.
15. Delete an evaluation result.

## Level 2.4: Human Feedback and Correction System

DriftGuard AI now supports human-in-the-loop evaluation. Users can review each evaluated case, correct labels, drift types, severity, add reviewer notes, and export corrected datasets for future training.

Local feedback storage:

```text
backend/storage/feedback/
```

This level still uses local JSON file storage only. A real database and authentication can be added in production levels.

Testing flow:

1. Start backend.
2. Start frontend.
3. Open Dataset Evaluation.
4. Run sample evaluation or saved dataset evaluation.
5. Enable `Human Review Mode`.
6. Open one mismatched case.
7. Select corrected label, drift type, and severity.
8. Add reviewer notes.
9. Click `Save Feedback`.
10. Confirm feedback summary updates.
11. Confirm feedback appears in Human Feedback History.
12. Export corrected dataset.
13. Build training dataset.
14. Delete feedback and confirm UI updates.

## Level 2.5: Root Cause Analysis and Auto Fix Recommendation

DriftGuard AI now detects the probable root cause behind architectural drift, identifies the responsible source, recommends a fix, estimates priority and effort, suggests an owner/team, and generates an action plan.

Root cause categories:

- Documentation Outdated
- Code Behavior Changed
- Ticket Requirement Conflict
- Runtime Failure
- Configuration Mismatch
- Commit Introduced Drift
- Database/Config Drift
- Ambiguous Multi-Source Drift
- No Drift Detected
- Unknown

Testing flow:

1. Start backend.
2. Start frontend.
3. Open Dataset Evaluation.
4. Run sample or uploaded dataset evaluation.
5. Click `Generate Root Cause Analysis`.
6. Check root cause summary cards.
7. Check each case recommendation.
8. Export root cause JSON.
9. Export root cause Markdown.
10. Open Evaluation History.
11. Click `Root Cause` for an older evaluation.
12. Confirm the root cause report appears.

## Level 2.6: Architecture Drift Timeline and Impact Graph

DriftGuard AI now builds an inferred timeline of drift events and an impact graph showing relationships between documentation, code, Jira, commits, logs, config, components, and drift cases.

Timeline helps understand how drift evolved across sources. Impact graph helps identify affected components and the riskiest system areas.

Testing flow:

1. Start backend.
2. Start frontend.
3. Open Dataset Evaluation.
4. Run sample or uploaded dataset evaluation.
5. Click `Generate Drift Timeline`.
6. Check timeline cards and event order.
7. Export timeline JSON.
8. Export timeline Markdown.
9. Click `Generate Impact Graph`.
10. Check risky components.
11. Check graph relationship table.
12. Export impact graph JSON.
13. Open Evaluation History.
14. Generate timeline and impact graph for an older evaluation.

How to test:

1. Start backend:

```powershell
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

2. Start frontend:

```powershell
cd frontend
npm run dev
```

3. Open the Dataset Evaluation page.

4. Test sample dataset:

- Click `Load Sample Dataset`
- Click `Run Sample Evaluation`
- Check metrics, quality report, confusion matrix, and insights
- Export JSON
- Export Markdown

5. Test uploaded dataset:

- Download Dataset Template
- Upload the template JSON
- Preview Uploaded Dataset
- Evaluate Uploaded Dataset
- Check advanced evaluation analysis
- Export reports

## Sample Input

Documentation:

```text
The /api/payment/refund endpoint is public and can be accessed by customers without special internal permissions.
```

Code:

```python
@internal_only
@app.route("/api/payment/refund")
def refund_payment():
    return process_refund()
```

Jira:

```text
JIRA-231: Customer refund feature is completed and ready for production.
```

Commit:

```text
Added internal-only access to refund API for security compliance.
```

Logs:

```text
403 Forbidden: customer_123 tried to access /api/payment/refund
```

Database Config:

```text
access_type=internal, feature_enabled=true
```

## Expected Output

For the sample input, the system should output:

- Entity: `/api/payment/refund`
- Drift Type: `Documentation Drift` or `Implementation Drift`
- Severity: `Critical` or `High`
- Confidence Score: around `0.90` to `0.95`
- Recommended Action: `Generate documentation update PR` or `Create Jira ticket for engineering review`

## Level 2.7: Proactive Drift Monitoring and Alerts

DriftGuard AI now supports local monitoring rules for saved datasets. Users can manually run monitoring checks, generate alerts based on thresholds, track alert history, update alert status, and export alert reports.

This level uses local JSON file storage only. Monitoring data is saved under:

- `backend/storage/monitoring/rules/`
- `backend/storage/monitoring/runs/`
- `backend/storage/monitoring/alerts/`

Monitoring Rules:

- `POST /monitoring/rules`
- `GET /monitoring/rules`
- `GET /monitoring/rules/{rule_id}`
- `PUT /monitoring/rules/{rule_id}`
- `DELETE /monitoring/rules/{rule_id}`

Monitoring Runs:

- `POST /monitoring/rules/{rule_id}/run`
- `GET /monitoring/runs`
- `GET /monitoring/runs/{run_id}`
- `DELETE /monitoring/runs/{run_id}`

Alerts:

- `GET /monitoring/alerts`
- `GET /monitoring/alerts/{alert_id}`
- `PUT /monitoring/alerts/{alert_id}/status`
- `DELETE /monitoring/alerts/{alert_id}`
- `GET /monitoring/alerts/export-json`
- `GET /monitoring/alerts/export-markdown`

Testing flow:

1. Start backend.
2. Start frontend.
3. Save at least one uploaded dataset in Dataset Library.
4. Open Monitoring Dashboard.
5. Create a monitoring rule for a saved dataset.
6. Click `Run Check`.
7. Confirm monitoring run appears.
8. Confirm alerts appear if thresholds are violated.
9. Change alert status to acknowledged.
10. Change alert status to resolved.
11. Export alerts JSON.
12. Export alerts Markdown.
13. Delete alert.
14. Delete monitoring run.
15. Delete monitoring rule.

This level uses manual monitoring runs only. Real background scheduling can be added in the next production level.

## Level 2.8: Authentication, Workspaces, and Role-Based Access Control

DriftGuard AI now supports local login/signup, 24-hour session tokens, workspace-based data separation, user profiles, user management, and role-based permission checks.

Local storage folders:

```text
backend/storage/auth/users/
backend/storage/auth/sessions/
backend/storage/workspaces/
```

Roles:

- `admin`: manage users, create workspaces, view all workspace data, save/delete datasets, run evaluations, manage monitoring, manage alerts, export reports, and delete history
- `engineer`: save datasets, run evaluations, create monitoring rules, acknowledge/manage alerts, and export reports
- `reviewer`: view evaluations, add human feedback, export corrected datasets, and build training datasets
- `viewer`: view dashboards only

Auth endpoints:

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /auth/users`
- `PUT /auth/users/{user_id}/role`
- `DELETE /auth/users/{user_id}`

Workspace endpoints:

- `POST /workspaces`
- `GET /workspaces`
- `GET /workspaces/{workspace_id}`
- `PUT /workspaces/{workspace_id}`
- `DELETE /workspaces/{workspace_id}`
- `POST /workspaces/{workspace_id}/members`
- `DELETE /workspaces/{workspace_id}/members/{user_id}`
- `GET /workspaces/{workspace_id}/members`

Workspace-scoped data now includes saved datasets, evaluation history, feedback items, monitoring rules, monitoring runs, and alerts. Dataset, evaluation, feedback, and monitoring list endpoints accept `workspace_id`.

Testing flow:

1. Start backend.
2. Start frontend.
3. Open app.
4. Signup as the first admin user.
5. Login.
6. Create a workspace.
7. Upload and save a dataset under the workspace.
8. Run an evaluation.
9. Confirm the dataset appears only in the selected workspace.
10. Create another user.
11. Change role to viewer.
12. Login as viewer.
13. Confirm viewer cannot run evaluation or delete/export.
14. Login as reviewer.
15. Confirm reviewer can add feedback but cannot create monitoring rule.
16. Login as engineer.
17. Confirm engineer can run evaluation and monitoring.
18. Login as admin.
19. Confirm admin can manage users and delete history.

## Level 2.9: Enterprise Audit Trail and Compliance Governance

DriftGuard AI now records workspace-level audit events for user actions, permission failures, exports, deletions, monitoring actions, evaluations, and governance events. Admins can review audit logs, filter events, export reports, delete audit events, and view compliance risk summaries.

Local audit storage:

```text
backend/storage/audit/
```

Audit endpoints:

- `GET /audit/events`
- `GET /audit/events/{audit_id}`
- `GET /audit/summary`
- `GET /audit/compliance-risk`
- `GET /audit/export-json`
- `GET /audit/export-markdown`
- `DELETE /audit/events/{audit_id}`

Audit events track:

- Authentication events such as signup, login, logout, failed login, invalid token
- Workspace governance such as create/update/delete workspace and member changes
- User management such as role updates and user deletion
- Dataset and evaluation actions such as save, view, run, compare, delete, and export
- Feedback, root cause, timeline, impact graph, monitoring, and alert actions
- Security events such as permission denied and unauthorized access attempts

Testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin.
4. Create workspace.
5. Save dataset.
6. Run evaluation.
7. Export report.
8. Delete an evaluation or dataset.
9. Login as viewer.
10. Try restricted action.
11. Login back as admin.
12. Open Audit Dashboard.
13. Confirm actions are logged.
14. Confirm permission denied event is logged.
15. Apply filters.
16. View compliance risk summary.
17. Export audit JSON.
18. Export audit Markdown.

## Level 3.0: Database Persistence and Migration

DriftGuard AI now supports SQLite database storage for production-style persistence while keeping JSON storage compatibility. The system includes SQLAlchemy ORM models, a repository layer, JSON-to-database migration, backup, restore, database health checks, and integrity validation.

SQLite database path:

```text
backend/storage/driftguard.db
```

System Database endpoints:

- `GET /system/database/health`
- `POST /system/database/migrate-json`
- `GET /system/database/backup`
- `POST /system/database/restore`
- `GET /system/database/integrity`

Migration command:

```powershell
cd backend
python -m database.migrate_json_to_db
```

Run backend:

```powershell
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

Run frontend:

```powershell
cd frontend
npm run dev
```

Testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin.
4. Open System Admin Dashboard.
5. Check database health.
6. Run JSON-to-database migration.
7. Confirm migration summary.
8. Open Dataset Library and confirm data still appears.
9. Run evaluation and confirm evaluation is stored.
10. Open Audit Dashboard and confirm events are stored.
11. Download database backup.
12. Run integrity check.
13. Confirm status is clean.

SQLite is used for local development. PostgreSQL can be added later by changing `DATABASE_URL` and using the same repository layer.

## Level 3.1: Enterprise Source Connectors

DriftGuard AI now supports importing real enterprise sources such as GitHub repositories, Jira-style ticket exports, Confluence-style documentation exports, logs, and configuration files. Imported sources are normalized, stored in the active workspace, searchable from the Connector Dashboard, and convertible into evaluation-ready datasets with uncertain labels for later human review.

Connector types:

- `github`
- `jira`
- `confluence`
- `logs`
- `config`
- `manual_upload`

Connector endpoints:

- `POST /connectors`
- `GET /connectors`
- `GET /connectors/{connector_id}`
- `PUT /connectors/{connector_id}`
- `DELETE /connectors/{connector_id}`
- `POST /connectors/{connector_id}/test`
- `POST /connectors/{connector_id}/sync`
- `GET /connectors/{connector_id}/sync-runs`

Source endpoints:

- `GET /sources`
- `GET /sources/{source_id}`
- `DELETE /sources/{source_id}`
- `POST /sources/generate-dataset`
- `POST /sources/generate-dataset-from-connector/{connector_id}`
- `POST /connectors/upload-sources`

Connector testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin or engineer.
4. Open Connectors page.
5. Create GitHub connector using a public GitHub repo URL.
6. Test connection.
7. Sync repository.
8. Confirm imported sources appear.
9. Upload Jira-style JSON/CSV ticket file.
10. Upload documentation markdown file.
11. Upload logs file.
12. Select imported sources.
13. Generate dataset from selected sources.
14. Open Dataset Library.
15. Confirm generated dataset appears.
16. Run evaluation on generated dataset.
17. Use Human Review Mode to correct uncertain labels.

Credential warning:

Access tokens are stored locally for MVP development only. For production, use encrypted secrets management.

## Level 3.2: RAG-Based Cross-Silo Semantic Search

DriftGuard AI now supports workspace-scoped search across imported documentation, code, tickets, logs, and config. It chunks imported sources, retrieves relevant evidence locally, and generates structured answers with possible drift hints.

This MVP uses local keyword/TF-IDF-style retrieval and does not require paid embeddings, external LLM APIs, external API keys, or Streamlit.

RAG Search endpoints:

- `POST /rag/index`
- `POST /rag/search`
- `GET /rag/chunks`
- `GET /rag/search-history`
- `GET /rag/search-history/{query_id}`
- `GET /rag/search-history/{query_id}/export-markdown`

Search testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin or engineer.
4. Import sources using Connectors page.
5. Rebuild Search Index.
6. Open Search page.
7. Ask: `Why is refund API failing?`
8. Check answer card.
9. Check evidence cards.
10. Check source coverage.
11. Export search answer as Markdown.
12. Confirm search history is saved.

## Level 3.3: Agent Workflow Orchestrator

DriftGuard AI now supports agentic drift investigation. Users can provide a high-level goal, and the system creates a plan, executes multi-step analysis, retrieves evidence, generates datasets, runs evaluation, performs root cause analysis, builds timeline and impact graph, and produces a final report.

The MVP uses local rule-based planning and orchestration. It does not require paid APIs, external API keys, or Streamlit.

Agent endpoints:

- `POST /agent/plan`
- `POST /agent/run`
- `GET /agent/runs`
- `GET /agent/runs/{run_id}`
- `DELETE /agent/runs/{run_id}`
- `GET /agent/runs/{run_id}/export-json`
- `GET /agent/runs/{run_id}/export-markdown`

Agent testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin or engineer.
4. Import sources using Connectors.
5. Rebuild Search Index.
6. Open Agent page.
7. Enter goal: `Check payment module drift and prepare a full report.`
8. Click Generate Plan.
9. Check generated workflow steps.
10. Click Run Agent Workflow.
11. Check step execution logs.
12. Check final agent report.
13. Export report as Markdown.
14. Open Agent Run History.
15. View older run.

## Level 3.4: LLM-Ready Hybrid Intelligence Layer

DriftGuard AI now supports a hybrid intelligence architecture. It works in local-only mode by default and can optionally use LLM providers such as OpenAI, Gemini, Ollama, or a custom provider. Hybrid mode compares local rule-based reasoning with LLM output, validates results, and stores reasoning traces.

External LLM providers are optional. The application works fully in local-only mode without API keys.

Reasoning modes:

- `local_only`
- `llm_only`
- `hybrid`

Provider options:

- `local`
- `openai`
- `gemini`
- `ollama`
- `custom`

LLM Settings endpoints:

- `GET /llm/settings`
- `POST /llm/settings`
- `PUT /llm/settings/{settings_id}`
- `DELETE /llm/settings/{settings_id}`

Prompt Template endpoints:

- `GET /llm/prompts`
- `POST /llm/prompts`
- `PUT /llm/prompts/{template_id}`
- `DELETE /llm/prompts/{template_id}`

Reasoning endpoints:

- `POST /llm/reason`
- `GET /llm/traces`
- `GET /llm/traces/{trace_id}`
- `GET /llm/hybrid-results`
- `GET /llm/hybrid-results/{result_id}`
- `PUT /llm/hybrid-results/{result_id}/approval`
- `GET /llm/traces/{trace_id}/export-markdown`

Hybrid intelligence testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin or engineer.
4. Open AI Settings page.
5. Confirm local provider is available.
6. Save local_only settings.
7. Run Manual Analysis with local_only.
8. Run Hybrid Reasoning with provider local.
9. Check reasoning trace.
10. Export trace as Markdown.
11. Approve a hybrid result.
12. Confirm audit event is created.

## Level 3.5: Production Deployment with Docker

DriftGuard AI can now run using Docker and Docker Compose with persistent SQLite storage, environment configuration, health checks, basic security headers, production logging, and a CI workflow.

Local development backend:

```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

Local development frontend:

```bash
cd frontend
npm run dev
```

Docker environment setup:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp .env.example .env
```

Run with Docker Compose:

```bash
docker compose up --build
```

Stop Docker Compose:

```bash
docker compose down
```

URLs:

- Frontend: http://localhost:5173
- Backend: http://localhost:8001
- Health: http://localhost:8001/health
- Readiness: http://localhost:8001/system/ready

Docker storage:

- SQLite and local storage persist in the `driftguard_storage` Docker volume.
- The database file is not copied into the backend image.

Deployment files:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.github/workflows/ci.yml`
- `DEPLOYMENT.md`
- `SECURITY.md`
- `TROUBLESHOOTING.md`

## Level 3.6 Lite: Testing and Reliability

This is Level 3.6 Lite because only essential QA and reliability features are added first.

Backend tests:

```bash
cd backend
pytest
```

Demo seed:

```bash
cd backend
python -m scripts.seed_demo_data
```

Frontend build:

```bash
cd frontend
npm run build
```

Demo credentials:

- Email: `admin@driftguard.local`
- Password: `admin1234`

Reliability additions:

- Basic pytest setup for health, readiness, and auth behavior
- Standard backend error response helper
- Global exception handlers that avoid exposing stack traces
- `X-Request-ID` response header for each request
- React error boundary with reload option
- Demo seed script for admin, workspace, and sample imported sources

## Level 3.7: QA Automation and Observability

DriftGuard AI now includes broader backend tests, frontend smoke tests, request metrics, error tracking, slow endpoint detection, and an admin-only observability dashboard.

Backend tests:

```bash
cd backend
pytest
```

Frontend tests:

```bash
cd frontend
npm run test
```

Observability:

- Admin users can open the Observability page to inspect request metrics and backend errors.
- Request metrics are stored locally in `backend/storage/observability/request_metrics.json`.
- Error events are stored locally in `backend/storage/observability/error_events.json`.
- `/observability/summary`, `/observability/requests`, `/observability/errors`, and `/observability/health-performance` are admin-only endpoints.

## Level 3.8: Security Hardening and Data Privacy Controls

DriftGuard AI now includes stronger password handling, account lockout, API rate limiting, secrets redaction, sensitive data detection, workspace privacy settings, workspace export, a delete request workflow, and an admin-only Security dashboard.

Auth Sessions:

- `GET /auth/sessions`
- `DELETE /auth/sessions/{session_id}`

Privacy:

- `GET /privacy/settings`
- `PUT /privacy/settings`
- `GET /privacy/workspace/{workspace_id}/export`
- `POST /privacy/workspace/{workspace_id}/delete-request`
- `GET /privacy/delete-requests`
- `POST /privacy/delete-requests/{delete_request_id}/approve`

Security:

- `GET /security/summary`
- `GET /security/events`

Notes:

- New passwords must be at least 8 characters and include at least one letter and one number.
- Failed login attempts lock an account temporarily after repeated failures.
- Rate limiting is local in-memory by default and does not require Redis.
- Privacy mode redacts sensitive values in response previews and exports without destroying original stored source content.

## Level 3.9: Benchmark Dataset Integration and Training Data Pipeline

DriftGuard AI now supports importing public benchmark datasets such as CosQA, SNLI, CommitPack, and Spider. These datasets can be converted into DriftGuard-compatible cases, analyzed for quality, split into train/validation/test sets, merged with human-corrected examples, and exported as training-ready JSONL or JSON.

Dataset roles:

- CosQA: code-text alignment
- SNLI: contradiction detection
- CommitPack: commit/code change reasoning
- Spider: database/config reasoning

Benchmark:

- `GET /benchmarks/registry`
- `POST /benchmarks/upload`
- `GET /benchmarks`
- `GET /benchmarks/{benchmark_id}`
- `GET /benchmarks/{benchmark_id}/examples`
- `POST /benchmarks/{benchmark_id}/create-driftguard-dataset`
- `POST /benchmarks/{benchmark_id}/split`
- `GET /benchmarks/{benchmark_id}/quality`
- `DELETE /benchmarks/{benchmark_id}`

Training:

- `POST /benchmarks/training/merge`
- `POST /benchmarks/training/export`
- `GET /benchmarks/training/exports`
- `GET /benchmarks/training/exports/{export_id}/download`

Testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin or engineer.
4. Open Training Data page.
5. View dataset registry.
6. Upload small SNLI/CosQA-style JSON sample.
7. Confirm examples import.
8. View quality report.
9. Create train/validation/test split.
10. Convert benchmark to DriftGuard dataset.
11. Open Dataset Library and run evaluation.
12. Export training JSONL.
13. Download export.

Notes:

- Benchmark uploads are local files only and do not require paid APIs or external keys.
- SQLite remains the default storage engine.
- Privacy redaction is applied to benchmark previews and training exports when workspace privacy settings require it.

## Level 4.0: Model Training Sandbox and Evaluation Leaderboard

DriftGuard AI now supports lightweight local model training using TF-IDF and classical ML models. Users can train label, severity, and drift type classifiers, compare experiments on a leaderboard, deploy selected local models, run predictions, export experiment reports, and rollback to the rule-based engine.

Supported models:

- Logistic Regression
- Linear SVM
- Multinomial Naive Bayes
- Random Forest

Supported tasks:

- `label_classification`
- `severity_classification`
- `drift_type_classification`

ML Training:

- `POST /ml/experiments/train`
- `GET /ml/experiments`
- `GET /ml/experiments/{experiment_id}`
- `DELETE /ml/experiments/{experiment_id}`
- `GET /ml/leaderboard`
- `GET /ml/experiments/compare`
- `POST /ml/experiments/{experiment_id}/deploy`
- `POST /ml/deployed/{task_type}/rollback`
- `GET /ml/deployed`
- `POST /ml/predict`
- `GET /ml/experiments/{experiment_id}/export-markdown`

Testing flow:

1. Start backend.
2. Start frontend.
3. Login as admin or engineer.
4. Open Training Data page.
5. Import or prepare benchmark examples.
6. Export training dataset.
7. Open Models page.
8. Start logistic regression label classifier training.
9. Check leaderboard.
10. Open experiment detail.
11. Deploy model.
12. Run prediction.
13. Rollback model.
14. Confirm rule-based fallback works.

Notes:

- Training uses local scikit-learn only and does not require GPU, paid APIs, or external keys.
- Datasets with fewer than 10 labeled examples or only one class are rejected with clear errors.
- The rule-based engine remains the fallback when no model is deployed.

## Level 4.4: Incident Management, Webhooks, and Escalation Automation

DriftGuard AI now includes an incident management layer for turning drift findings into accountable operational work. Incidents support severity, status, ownership, source links, comments, timeline events, SLA due dates, markdown export, webhook notifications, delivery logs, and escalation rules.

Incident permissions:

- Admin: view, manage, delete incidents, and manage incident automation.
- Engineer: view and manage incidents, webhooks, and escalation rules.
- Reviewer: view and manage incidents.
- Viewer: read-only incident access.

Incident workflow:

1. Open the Incidents page.
2. Create a manual incident or create one from a monitoring alert through `POST /incidents/from-alert`.
3. Assign an owner and update status as work progresses.
4. Add comments for review notes and handoffs.
5. Export the incident report as Markdown when needed.
6. Configure webhooks for incident events.
7. Configure escalation rules and run `POST /incidents/escalations/check`.

Configuration:

- `INCIDENT_AUTO_CREATE_ENABLED=false`
- `INCIDENT_AUTO_CREATE_SEVERITIES=Critical,High`
- `WEBHOOK_TIMEOUT_SECONDS=5`

Notes:

- Webhook failures are recorded in delivery logs and do not block incident lifecycle changes.
- Level 4.4 currently integrates directly with monitoring alerts. Model-drift and active-learning incident sources are stored as optional relation fields for future Level 4.1-4.3 integrations.
- SQLite remains the default local persistence layer.

## Level 4.5: External Workflow Integrations

DriftGuard AI now supports external workflow integrations. Incidents can be synced to Jira-style tickets, GitHub Issues, Slack/Teams notifications, and generic webhooks. Mock mode works without API keys for demos and is the default integration mode.

Supported integration types:

- `jira`
- `github_issues`
- `slack`
- `teams`
- `generic_webhook`

Integration modes:

- `mock`: no external API calls, creates local simulated external tickets/issues/messages.
- `live`: uses configured external API/webhook credentials when provided; missing credentials return clear errors.

Integration endpoints:

- `POST /integrations`
- `GET /integrations`
- `GET /integrations/{integration_id}`
- `PUT /integrations/{integration_id}`
- `DELETE /integrations/{integration_id}`
- `POST /integrations/{integration_id}/test`
- `POST /integrations/{integration_id}/incident/{incident_id}/sync`
- `POST /integrations/{integration_id}/incident/{incident_id}/notify`
- `GET /integrations/sync-records`
- `GET /integrations/linked-resources`
- `GET /integrations/health-summary`
- `GET /integrations/mock-items`

Testing flow:

1. Open Integrations page.
2. Create Jira integration in mock mode.
3. Test integration.
4. Open Incidents page and create incident.
5. Sync incident to mock Jira.
6. Confirm mock external ticket appears.
7. Create GitHub issue mock integration.
8. Sync same incident to GitHub mock.
9. Check linked resources.
10. Check sync records.

Notes:

- Mock mode requires no paid APIs or external API keys.
- Secrets are masked in API responses.
- Privacy export redaction is applied to outgoing incident payloads when workspace privacy mode and export redaction are enabled.
- Live providers are intentionally simple wrappers and should be backed by secure secret storage and retry queues in production.

## Level 4.6: Executive Reporting and Enterprise Demo Mode

DriftGuard AI now includes an executive dashboard that summarizes drift risk, incidents, model health, compliance, integrations, and estimated ROI. It also includes demo mode for guided product walkthroughs.

Executive endpoints:

- `GET /executive/metrics`
- `POST /executive/roi`
- `POST /executive/report`
- `GET /executive/reports`
- `GET /executive/reports/{report_id}`
- `GET /executive/reports/{report_id}/export-markdown`

Demo endpoints:

- `GET /demo/scenarios`
- `POST /demo/enable`
- `POST /demo/disable`
- `GET /demo/state`
- `POST /demo/advance-step`
- `POST /demo/reset`
- `POST /demo/seed-executive-demo`

Testing flow:

1. Open Executive page.
2. Check KPI cards.
3. Calculate ROI.
4. Generate executive report.
5. Export report markdown.
6. Enable demo mode.
7. Advance demo step.
8. Seed executive demo data.
9. Reset demo data as admin.

Notes:

- ROI is calculated locally from configurable assumptions.
- Executive reports respect workspace privacy export redaction.
- Demo reset is conservative and does not delete user accounts or normal workspace data.
- Demo seed creates mock integration and incident data without external API keys.

## Level 4.7: Real-World Validation and Research Results Generator

DriftGuard AI now includes an end-to-end validation suite for real and demo datasets. It can run full-system validation, aggregate metrics, compare baselines, run ablation studies, generate research-ready reports, and export results as JSON, CSV, and Markdown.

Validation endpoints:

- `POST /validation/run-real-dataset`
- `POST /validation/run-full-system`
- `POST /validation/run-demo-scenario`
- `GET /validation/runs`
- `GET /validation/runs/{validation_id}`
- `DELETE /validation/runs/{validation_id}`
- `POST /validation/runs/{validation_id}/research-report`
- `GET /validation/runs/{validation_id}/research-report/export-markdown`
- `GET /validation/runs/{validation_id}/export-json`
- `GET /validation/runs/{validation_id}/export-csv`
- `POST /validation/baseline-comparison`
- `POST /validation/ablation-study`
- `GET /validation/demo-readiness`
- `GET /validation/research-results`

Testing flow:

1. Open Validation page.
2. Check demo readiness.
3. Run real dataset validation.
4. View validation results.
5. Run baseline comparison.
6. Run ablation study.
7. Generate research report.
8. Export Markdown report.
9. Export JSON and CSV results.
10. Use report metrics in final PPT or research paper.

Notes:

- Validation metrics are generated from local MVP data and safe fallbacks.
- Baseline and ablation outputs are best-effort when ML/hybrid modules are unavailable.
- No paid APIs or external keys are required.

## Future Levels

- LLM-assisted claim extraction and reconciliation
- LangGraph workflow orchestration
- Vector search or graph storage for richer evidence retrieval
