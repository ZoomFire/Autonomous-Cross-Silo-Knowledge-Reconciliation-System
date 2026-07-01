export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/$/, "");

const WORKSPACE_KEY = "driftguard_workspace_id";

export function setSelectedWorkspaceId(workspaceId) {
  localStorage.setItem(WORKSPACE_KEY, workspaceId || "");
  window.dispatchEvent(new Event("driftguard-workspace-changed"));
}

export function getSelectedWorkspaceId() {
  return localStorage.getItem(WORKSPACE_KEY) || "";
}

function withWorkspace(path) {
  const workspaceId = getSelectedWorkspaceId();
  if (!workspaceId) return path;
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}workspace_id=${encodeURIComponent(workspaceId)}`;
}

async function errorMessageFromResponse(response, fallback) {
  try {
    const errorBody = await response.json();
    if (errorBody.message) return errorBody.message;
    if (errorBody.details?.message) return errorBody.details.message;
    if (typeof errorBody.detail === "string") return errorBody.detail;
    if (errorBody.detail?.message) return errorBody.detail.message;
  } catch {
  }
  if (response.status === 401) return "Request unauthorized.";
  if (response.status === 403) return "Permission denied for this action.";
  return fallback;
}

function networkErrorMessage(error) {
  if (error?.message === "Failed to fetch" || error instanceof TypeError) {
    return "Backend unavailable. Please check that the server is running.";
  }
  return error?.message || "Request failed.";
}

function apiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function logNetworkError(url, error) {
  console.error("[DriftGuard API] Backend request failed", {
    url,
    apiBaseUrl: API_BASE_URL || "(same-origin)",
    message: error?.message || String(error),
  });
}

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };
  const fetchOptions = { ...options };
  const url = apiUrl(path);
  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    });

    if (response.ok) {
      return response.json();
    }

    const message = await errorMessageFromResponse(response, `Request failed with status ${response.status}`);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  } catch (err) {
    if (err instanceof TypeError) {
      logNetworkError(url, err);
      throw new Error(networkErrorMessage(err));
    }
    throw err;
  }
}

export function analyzeDrift(payload) {
  return request(withWorkspace("/analyze"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getReports() {
  return request("/reports");
}

export function getHealth() {
  return request("/health");
}

export function getSampleDataset() {
  return request("/dataset/sample");
}

export function runDatasetEvaluation() {
  return request(withWorkspace("/dataset/evaluate"), {
    method: "POST",
  });
}

export function uploadDatasetPreview(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/dataset/upload-preview", {
    method: "POST",
    body: formData,
  });
}

export function uploadDatasetEvaluate(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("workspace_id", getSelectedWorkspaceId());
  return request("/dataset/upload-evaluate", {
    method: "POST",
    body: formData,
  });
}

export function saveUploadedDataset(file, name, description, version) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("name", name);
  formData.append("description", description || "");
  formData.append("version", version || "1.0");
  formData.append("workspace_id", getSelectedWorkspaceId());
  return request("/dataset/save-uploaded", {
    method: "POST",
    body: formData,
  });
}

export function getDatasetLibrary() {
  return request(withWorkspace("/dataset/library"));
}

export function getSavedDataset(datasetId) {
  return request(withWorkspace(`/dataset/library/${datasetId}`));
}

export function deleteSavedDataset(datasetId) {
  return request(withWorkspace(`/dataset/library/${datasetId}`), { method: "DELETE" });
}

export function evaluateSavedDataset(datasetId) {
  return request(withWorkspace(`/dataset/library/${datasetId}/evaluate`), { method: "POST" });
}

export function getEvaluationHistory() {
  return request(withWorkspace("/dataset/evaluations/history"));
}

export function getEvaluationResult(evaluationId) {
  return request(withWorkspace(`/dataset/evaluations/history/${evaluationId}`));
}

export function deleteEvaluationResult(evaluationId) {
  return request(withWorkspace(`/dataset/evaluations/history/${evaluationId}`), { method: "DELETE" });
}

export function compareEvaluations(baseId, currentId) {
  return request(withWorkspace(`/dataset/evaluations/compare?base_id=${encodeURIComponent(baseId)}&current_id=${encodeURIComponent(currentId)}`));
}

export function saveCaseFeedback(feedback) {
  return request(withWorkspace("/feedback/case"), {
    method: "POST",
    body: JSON.stringify(feedback),
  });
}

export function getAllFeedback() {
  return request(withWorkspace("/feedback"));
}

export function getFeedbackForEvaluation(evaluationId) {
  return request(withWorkspace(`/feedback/evaluation/${evaluationId}`));
}

export function getFeedbackSummaryForEvaluation(evaluationId) {
  return request(withWorkspace(`/feedback/evaluation/${evaluationId}/summary`));
}

export function deleteFeedback(feedbackId) {
  return request(`/feedback/${feedbackId}`, { method: "DELETE" });
}

async function downloadReport(path, filename) {
  const url = apiUrl(path);
  try {
    const response = await fetch(url, {
    });
    if (response.ok) {
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      return;
    }

    const message = await errorMessageFromResponse(response, "Please run an evaluation first.");
    throw new Error(message);
  } catch (err) {
    if (err instanceof TypeError) {
      logNetworkError(url, err);
      throw new Error(networkErrorMessage(err));
    }
    throw err;
  }
}

export function exportLatestEvaluationJson() {
  return downloadReport("/dataset/evaluation/latest/export-json", "driftguard-evaluation-report.json");
}

export function exportLatestEvaluationMarkdown() {
  return downloadReport("/dataset/evaluation/latest/export-markdown", "driftguard-evaluation-report.md");
}

export function exportCorrectedDataset(evaluationId) {
  return downloadReport(`/feedback/evaluation/${evaluationId}/export-corrected-dataset`, "driftguard-corrected-dataset.json");
}

export function buildTrainingDataset(evaluationId) {
  return downloadReport(`/feedback/evaluation/${evaluationId}/build-training-dataset`, "driftguard-training-dataset.json");
}

export function getLatestRootCauseReport() {
  return request("/root-cause/latest");
}

export function getRootCauseReportForEvaluation(evaluationId) {
  return request(`/root-cause/evaluation/${evaluationId}`);
}

export function exportLatestRootCauseJson() {
  return downloadReport("/root-cause/latest/export-json", "driftguard-root-cause-report.json");
}

export function exportLatestRootCauseMarkdown() {
  return downloadReport("/root-cause/latest/export-markdown", "driftguard-root-cause-report.md");
}

export function getLatestTimeline() {
  return request("/timeline/latest");
}

export function getTimelineForEvaluation(evaluationId) {
  return request(`/timeline/evaluation/${evaluationId}`);
}

export function exportLatestTimelineJson() {
  return downloadReport("/timeline/latest/export-json", "driftguard-timeline-report.json");
}

export function exportLatestTimelineMarkdown() {
  return downloadReport("/timeline/latest/export-markdown", "driftguard-timeline-report.md");
}

export function getLatestImpactGraph() {
  return request("/impact-graph/latest");
}

export function getImpactGraphForEvaluation(evaluationId) {
  return request(`/impact-graph/evaluation/${evaluationId}`);
}

export function exportLatestImpactGraphJson() {
  return downloadReport("/impact-graph/latest/export-json", "driftguard-impact-graph.json");
}

export function createMonitoringRule(rule) {
  return request("/monitoring/rules", { method: "POST", body: JSON.stringify({ ...rule, workspace_id: getSelectedWorkspaceId() }) });
}

export function getMonitoringRules() {
  return request(withWorkspace("/monitoring/rules"));
}

export function getMonitoringRule(ruleId) {
  return request(withWorkspace(`/monitoring/rules/${ruleId}`));
}

export function updateMonitoringRule(ruleId, rule) {
  return request(withWorkspace(`/monitoring/rules/${ruleId}`), { method: "PUT", body: JSON.stringify(rule) });
}

export function deleteMonitoringRule(ruleId) {
  return request(withWorkspace(`/monitoring/rules/${ruleId}`), { method: "DELETE" });
}

export function runMonitoringRule(ruleId) {
  return request(withWorkspace(`/monitoring/rules/${ruleId}/run`), { method: "POST" });
}

export function getMonitoringRuns() {
  return request(withWorkspace("/monitoring/runs"));
}

export function getMonitoringRun(runId) {
  return request(withWorkspace(`/monitoring/runs/${runId}`));
}

export function deleteMonitoringRun(runId) {
  return request(withWorkspace(`/monitoring/runs/${runId}`), { method: "DELETE" });
}

export function getMonitoringAlerts() {
  return request(withWorkspace("/monitoring/alerts"));
}

export function getMonitoringAlert(alertId) {
  return request(withWorkspace(`/monitoring/alerts/${alertId}`));
}

export function updateMonitoringAlertStatus(alertId, status) {
  return request(withWorkspace(`/monitoring/alerts/${alertId}/status`), { method: "PUT", body: JSON.stringify({ status }) });
}

export function deleteMonitoringAlert(alertId) {
  return request(withWorkspace(`/monitoring/alerts/${alertId}`), { method: "DELETE" });
}

export function exportMonitoringAlertsJson() {
  return downloadReport(withWorkspace("/monitoring/alerts/export-json"), "driftguard-monitoring-alerts.json");
}

export function exportMonitoringAlertsMarkdown() {
  return downloadReport(withWorkspace("/monitoring/alerts/export-markdown"), "driftguard-monitoring-alerts.md");
}

export function createWorkspace(data) {
  return request("/workspaces", { method: "POST", body: JSON.stringify(data) });
}

export function getWorkspaces() {
  return request("/workspaces");
}

export function getWorkspace(workspaceId) {
  return request(`/workspaces/${workspaceId}`);
}

export function updateWorkspace(workspaceId, data) {
  return request(`/workspaces/${workspaceId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteWorkspace(workspaceId) {
  return request(`/workspaces/${workspaceId}`, { method: "DELETE" });
}

export function addWorkspaceMember(workspaceId, data) {
  return request(`/workspaces/${workspaceId}/members`, { method: "POST", body: JSON.stringify(data) });
}

export function removeWorkspaceMember(workspaceId, userId) {
  return request(`/workspaces/${workspaceId}/members/${userId}`, { method: "DELETE" });
}

export function getWorkspaceMembers(workspaceId) {
  return request(`/workspaces/${workspaceId}/members`);
}

function queryString(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function getAuditEvents(filters = {}) {
  return request(`/audit/events${queryString(filters)}`);
}

export function getAuditEvent(auditId) {
  return request(`/audit/events/${auditId}`);
}

export function getAuditSummary(workspaceId = "") {
  return request(`/audit/summary${queryString({ workspace_id: workspaceId })}`);
}

export function getComplianceRisk(workspaceId = "") {
  return request(`/audit/compliance-risk${queryString({ workspace_id: workspaceId })}`);
}

export function exportAuditJson(workspaceId = "") {
  return downloadReport(`/audit/export-json${queryString({ workspace_id: workspaceId })}`, "driftguard-audit-report.json");
}

export function exportAuditMarkdown(workspaceId = "") {
  return downloadReport(`/audit/export-markdown${queryString({ workspace_id: workspaceId })}`, "driftguard-audit-report.md");
}

export function deleteAuditEvent(auditId) {
  return request(`/audit/events/${auditId}`, { method: "DELETE" });
}

export function getDatabaseHealth() {
  return request("/system/database/health");
}

export function migrateJsonToDatabase() {
  return request("/system/database/migrate-json", { method: "POST" });
}

export function downloadDatabaseBackup() {
  return downloadReport("/system/database/backup", "driftguard-database-backup.json");
}

export function restoreDatabaseBackup(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/system/database/restore", { method: "POST", body: formData });
}

export function getDatabaseIntegrity() {
  return request("/system/database/integrity");
}

export function getObservabilitySummary() {
  return request("/observability/summary");
}

export function getObservabilityRequests(filters = {}) {
  return request(`/observability/requests${queryString(filters)}`);
}

export function getObservabilityErrors() {
  return request("/observability/errors");
}

export function getPerformanceHealth() {
  return request("/observability/health-performance");
}

export function getPrivacySettings(workspaceId) {
  return request(`/privacy/settings${queryString({ workspace_id: workspaceId })}`);
}

export function updatePrivacySettings(data) {
  return request("/privacy/settings", { method: "PUT", body: JSON.stringify(data) });
}

export function exportWorkspaceData(workspaceId) {
  return downloadReport(`/privacy/workspace/${workspaceId}/export`, `driftguard-workspace-${workspaceId.slice(0, 8)}-export.json`);
}

export function createWorkspaceDeleteRequest(workspaceId) {
  return request(`/privacy/workspace/${workspaceId}/delete-request`, { method: "POST" });
}

export function getWorkspaceDeleteRequests() {
  return request("/privacy/delete-requests");
}

export function approveWorkspaceDeleteRequest(requestId) {
  return request(`/privacy/delete-requests/${requestId}/approve`, { method: "POST" });
}

export function getSecuritySummary() {
  return request("/security/summary");
}

export function getSecurityEvents() {
  return request("/security/events");
}

export function getBenchmarkRegistry() {
  return request("/benchmarks/registry");
}

export function uploadBenchmarkDataset(formData) {
  if (!formData.has("workspace_id")) {
    formData.append("workspace_id", getSelectedWorkspaceId());
  }
  return request("/benchmarks/upload", { method: "POST", body: formData });
}

export function getBenchmarkDatasets(workspaceId = getSelectedWorkspaceId()) {
  return request(`/benchmarks${queryString({ workspace_id: workspaceId })}`);
}

export function getBenchmarkDataset(benchmarkId) {
  return request(`/benchmarks/${benchmarkId}`);
}

export function getBenchmarkExamples(benchmarkId, filters = {}) {
  return request(`/benchmarks/${benchmarkId}/examples${queryString(filters)}`);
}

export function createDriftGuardDatasetFromBenchmark(benchmarkId, data) {
  return request(`/benchmarks/${benchmarkId}/create-driftguard-dataset`, { method: "POST", body: JSON.stringify(data) });
}

export function createBenchmarkSplit(benchmarkId, data) {
  return request(`/benchmarks/${benchmarkId}/split`, { method: "POST", body: JSON.stringify(data) });
}

export function getBenchmarkQuality(benchmarkId) {
  return request(`/benchmarks/${benchmarkId}/quality`);
}

export function mergeTrainingData(data) {
  return request("/benchmarks/training/merge", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function exportTrainingDataset(data) {
  return request("/benchmarks/training/export", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getTrainingExports(workspaceId = getSelectedWorkspaceId()) {
  return request(`/benchmarks/training/exports${queryString({ workspace_id: workspaceId })}`);
}

export function downloadTrainingExport(exportId, format = "jsonl") {
  const extension = format === "json" ? "json" : "jsonl";
  return downloadReport(`/benchmarks/training/exports/${exportId}/download`, `driftguard-training-export-${exportId.slice(0, 8)}.${extension}`);
}

export function deleteBenchmarkDataset(benchmarkId) {
  return request(`/benchmarks/${benchmarkId}`, { method: "DELETE" });
}

export function trainModelExperiment(data) {
  return request("/ml/experiments/train", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getModelExperiments(filters = {}) {
  return request(`/ml/experiments${queryString({ workspace_id: getSelectedWorkspaceId(), ...filters })}`);
}

export function getModelExperiment(experimentId) {
  return request(`/ml/experiments/${experimentId}`);
}

export function deleteModelExperiment(experimentId) {
  return request(`/ml/experiments/${experimentId}`, { method: "DELETE" });
}

export function getModelLeaderboard(workspaceId = getSelectedWorkspaceId(), taskType = "") {
  return request(`/ml/leaderboard${queryString({ workspace_id: workspaceId, task_type: taskType })}`);
}

export function compareModelExperiments(baseId, currentId) {
  return request(`/ml/experiments/compare${queryString({ base_id: baseId, current_id: currentId })}`);
}

export function deployModelExperiment(experimentId) {
  return request(`/ml/experiments/${experimentId}/deploy`, { method: "POST" });
}

export function rollbackDeployedModel(taskType, workspaceId = getSelectedWorkspaceId()) {
  return request(`/ml/deployed/${taskType}/rollback`, { method: "POST", body: JSON.stringify({ workspace_id: workspaceId }) });
}

export function getDeployedModels(workspaceId = getSelectedWorkspaceId()) {
  return request(`/ml/deployed${queryString({ workspace_id: workspaceId })}`);
}

export function predictWithMLModel(data) {
  return request("/ml/predict", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function exportModelExperimentMarkdown(experimentId) {
  return downloadReport(`/ml/experiments/${experimentId}/export-markdown`, `driftguard-model-experiment-${experimentId.slice(0, 8)}.md`);
}

export function createIncident(data) {
  return request("/incidents", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function createIncidentFromAlert(data) {
  return request("/incidents/from-alert", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getIncidents(workspaceId = getSelectedWorkspaceId(), filters = {}) {
  return request(`/incidents${queryString({ workspace_id: workspaceId, ...filters })}`);
}

export function getIncident(incidentId) {
  return request(`/incidents/${incidentId}`);
}

export function updateIncidentStatus(incidentId, status) {
  return request(`/incidents/${incidentId}/status`, { method: "PUT", body: JSON.stringify({ status }) });
}

export function assignIncident(incidentId, assignedTo) {
  return request(`/incidents/${incidentId}/assign`, { method: "PUT", body: JSON.stringify({ assigned_to: assignedTo }) });
}

export function addIncidentComment(incidentId, commentText) {
  return request(`/incidents/${incidentId}/comments`, { method: "POST", body: JSON.stringify({ comment_text: commentText }) });
}

export function deleteIncident(incidentId) {
  return request(`/incidents/${incidentId}`, { method: "DELETE" });
}

export function exportIncidentMarkdown(incidentId) {
  return downloadReport(`/incidents/${incidentId}/export-markdown`, `driftguard-incident-${incidentId.slice(0, 8)}.md`);
}

export function getIncidentSummary(workspaceId = getSelectedWorkspaceId()) {
  return request(`/incidents/summary${queryString({ workspace_id: workspaceId })}`);
}

export function createIncidentWebhook(data) {
  return request("/incidents/webhooks", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getIncidentWebhooks(workspaceId = getSelectedWorkspaceId()) {
  return request(`/incidents/webhooks${queryString({ workspace_id: workspaceId })}`);
}

export function updateIncidentWebhook(webhookId, workspaceId, data) {
  return request(`/incidents/webhooks/${webhookId}${queryString({ workspace_id: workspaceId })}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteIncidentWebhook(webhookId, workspaceId = getSelectedWorkspaceId()) {
  return request(`/incidents/webhooks/${webhookId}${queryString({ workspace_id: workspaceId })}`, { method: "DELETE" });
}

export function testIncidentWebhook(webhookId, workspaceId = getSelectedWorkspaceId()) {
  return request(`/incidents/webhooks/${webhookId}/test${queryString({ workspace_id: workspaceId })}`, { method: "POST" });
}

export function getIncidentNotificationLogs(workspaceId = getSelectedWorkspaceId(), limit = 100) {
  return request(`/incidents/notification-logs${queryString({ workspace_id: workspaceId, limit })}`);
}

export function createEscalationRule(data) {
  return request("/incidents/escalation-rules", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getEscalationRules(workspaceId = getSelectedWorkspaceId()) {
  return request(`/incidents/escalation-rules${queryString({ workspace_id: workspaceId })}`);
}

export function updateEscalationRule(ruleId, workspaceId, data) {
  return request(`/incidents/escalation-rules/${ruleId}${queryString({ workspace_id: workspaceId })}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteEscalationRule(ruleId, workspaceId = getSelectedWorkspaceId()) {
  return request(`/incidents/escalation-rules/${ruleId}${queryString({ workspace_id: workspaceId })}`, { method: "DELETE" });
}

export function checkIncidentEscalations(workspaceId = getSelectedWorkspaceId()) {
  return request("/incidents/escalations/check", { method: "POST", body: JSON.stringify({ workspace_id: workspaceId }) });
}

export function createIntegration(data) {
  return request("/integrations", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getIntegrations(workspaceId = getSelectedWorkspaceId()) {
  return request(`/integrations${queryString({ workspace_id: workspaceId })}`);
}

export function getIntegration(integrationId) {
  return request(`/integrations/${integrationId}`);
}

export function updateIntegration(integrationId, data) {
  return request(`/integrations/${integrationId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteIntegration(integrationId) {
  return request(`/integrations/${integrationId}`, { method: "DELETE" });
}

export function testIntegration(integrationId) {
  return request(`/integrations/${integrationId}/test`, { method: "POST" });
}

export function syncIncidentToExternal(integrationId, incidentId) {
  return request(`/integrations/${integrationId}/incident/${incidentId}/sync`, { method: "POST" });
}

export function notifyIncidentExternal(integrationId, incidentId) {
  return request(`/integrations/${integrationId}/incident/${incidentId}/notify`, { method: "POST" });
}

export function getIntegrationSyncRecords(filters = {}) {
  return request(`/integrations/sync-records${queryString({ workspace_id: getSelectedWorkspaceId(), ...filters })}`);
}

export function getExternalLinkedResources(filters = {}) {
  return request(`/integrations/linked-resources${queryString({ workspace_id: getSelectedWorkspaceId(), ...filters })}`);
}

export function getIntegrationHealthSummary(workspaceId = getSelectedWorkspaceId()) {
  return request(`/integrations/health-summary${queryString({ workspace_id: workspaceId })}`);
}

export function getMockExternalItems(workspaceId = getSelectedWorkspaceId()) {
  return request(`/integrations/mock-items${queryString({ workspace_id: workspaceId })}`);
}

export function getExecutiveMetrics(workspaceId = getSelectedWorkspaceId()) {
  return request(`/executive/metrics${queryString({ workspace_id: workspaceId })}`);
}

export function calculateExecutiveROI(data) {
  return request("/executive/roi", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function generateExecutiveReport(data) {
  return request("/executive/report", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getExecutiveReports(workspaceId = getSelectedWorkspaceId()) {
  return request(`/executive/reports${queryString({ workspace_id: workspaceId })}`);
}

export function getExecutiveReport(reportId) {
  return request(`/executive/reports/${reportId}`);
}

export function exportExecutiveReportMarkdown(reportId) {
  return downloadReport(`/executive/reports/${reportId}/export-markdown`, `driftguard-executive-report-${reportId.slice(0, 8)}.md`);
}

export function getDemoScenarios() {
  return request("/demo/scenarios");
}

export function enableDemoMode(data) {
  return request("/demo/enable", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function disableDemoMode(data) {
  return request("/demo/disable", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getDemoState(workspaceId = getSelectedWorkspaceId()) {
  return request(`/demo/state${queryString({ workspace_id: workspaceId })}`);
}

export function advanceDemoStep(workspaceId = getSelectedWorkspaceId()) {
  return request("/demo/advance-step", { method: "POST", body: JSON.stringify({ workspace_id: workspaceId }) });
}

export function resetDemoData(workspaceId = getSelectedWorkspaceId()) {
  return request("/demo/reset", { method: "POST", body: JSON.stringify({ workspace_id: workspaceId }) });
}

export function seedExecutiveDemoData(workspaceId = getSelectedWorkspaceId()) {
  return request("/demo/seed-executive-demo", { method: "POST", body: JSON.stringify({ workspace_id: workspaceId }) });
}

export function runRealDatasetValidation(data) {
  return request("/validation/run-real-dataset", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function runFullSystemValidation(data) {
  return request("/validation/run-full-system", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function runDemoScenarioValidation(data) {
  return request("/validation/run-demo-scenario", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getValidationRuns(workspaceId = getSelectedWorkspaceId()) {
  return request(`/validation/runs${queryString({ workspace_id: workspaceId })}`);
}

export function getValidationRun(validationId) {
  return request(`/validation/runs/${validationId}`);
}

export function deleteValidationRun(validationId) {
  return request(`/validation/runs/${validationId}`, { method: "DELETE" });
}

export function generateResearchReport(validationId) {
  return request(`/validation/runs/${validationId}/research-report`, { method: "POST" });
}

export function exportResearchReportMarkdown(validationId) {
  return downloadReport(`/validation/runs/${validationId}/research-report/export-markdown`, `driftguard-research-report-${validationId.slice(0, 8)}.md`);
}

export function exportValidationResultsJson(validationId) {
  return downloadReport(`/validation/runs/${validationId}/export-json`, `driftguard-validation-${validationId.slice(0, 8)}.json`);
}

export function exportValidationMetricsCsv(validationId) {
  return downloadReport(`/validation/runs/${validationId}/export-csv`, `driftguard-validation-${validationId.slice(0, 8)}.csv`);
}

export function runBaselineComparison(data) {
  return request("/validation/baseline-comparison", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function runAblationStudy(data) {
  return request("/validation/ablation-study", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getDemoReadiness(workspaceId = getSelectedWorkspaceId()) {
  return request(`/validation/demo-readiness${queryString({ workspace_id: workspaceId })}`);
}

export function getResearchResults(workspaceId = getSelectedWorkspaceId()) {
  return request(`/validation/research-results${queryString({ workspace_id: workspaceId })}`);
}

export function createConnector(data) {
  return request("/connectors", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getConnectors(workspaceId = getSelectedWorkspaceId()) {
  return request(`/connectors${queryString({ workspace_id: workspaceId })}`);
}

export function getConnector(connectorId) {
  return request(`/connectors/${connectorId}`);
}

export function updateConnector(connectorId, data) {
  return request(`/connectors/${connectorId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteConnector(connectorId) {
  return request(`/connectors/${connectorId}`, { method: "DELETE" });
}

export function testConnector(connectorId) {
  return request(`/connectors/${connectorId}/test`, { method: "POST" });
}

export function syncConnector(connectorId) {
  return request(`/connectors/${connectorId}/sync`, { method: "POST" });
}

export function getImportedSources(filters = {}) {
  return request(`/sources${queryString({ workspace_id: getSelectedWorkspaceId(), ...filters })}`);
}

export function getImportedSource(sourceId) {
  return request(`/sources/${sourceId}`);
}

export function deleteImportedSource(sourceId) {
  return request(`/sources/${sourceId}`, { method: "DELETE" });
}

export function getConnectorSyncRuns(connectorId) {
  return request(`/connectors/${connectorId}/sync-runs`);
}

export function generateDatasetFromSources(data) {
  return request("/sources/generate-dataset", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function generateDatasetFromConnector(connectorId, data = {}) {
  return request(`/sources/generate-dataset-from-connector/${connectorId}`, { method: "POST", body: JSON.stringify(data) });
}

export function uploadConnectorSources(formData) {
  if (!formData.has("workspace_id")) {
    formData.append("workspace_id", getSelectedWorkspaceId());
  }
  return request("/connectors/upload-sources", { method: "POST", body: formData });
}

export function buildRagIndex(workspaceId = getSelectedWorkspaceId()) {
  return request("/rag/index", { method: "POST", body: JSON.stringify({ workspace_id: workspaceId }) });
}

export function ragSearch(data) {
  return request("/rag/search", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getRagChunks(filters = {}) {
  return request(`/rag/chunks${queryString({ workspace_id: getSelectedWorkspaceId(), ...filters })}`);
}

export function getRagSearchHistory(workspaceId = getSelectedWorkspaceId()) {
  return request(`/rag/search-history${queryString({ workspace_id: workspaceId })}`);
}

export function getRagSearchHistoryItem(queryId) {
  return request(`/rag/search-history/${queryId}`);
}

export function exportRagSearchMarkdown(queryId) {
  return downloadReport(`/rag/search-history/${queryId}/export-markdown`, "driftguard-search-answer.md");
}

export function createAgentPlan(data) {
  return request("/agent/plan", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function runAgentWorkflow(data) {
  return request("/agent/run", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getAgentRuns(workspaceId = getSelectedWorkspaceId()) {
  return request(`/agent/runs${queryString({ workspace_id: workspaceId })}`);
}

export function getAgentRun(runId) {
  return request(`/agent/runs/${runId}`);
}

export function deleteAgentRun(runId) {
  return request(`/agent/runs/${runId}`, { method: "DELETE" });
}

export function exportAgentReportJson(runId) {
  return downloadReport(`/agent/runs/${runId}/export-json`, `driftguard-agent-report-${runId.slice(0, 8)}.json`);
}

export function exportAgentReportMarkdown(runId) {
  return downloadReport(`/agent/runs/${runId}/export-markdown`, `driftguard-agent-report-${runId.slice(0, 8)}.md`);
}

export function getLLMSettings(workspaceId = getSelectedWorkspaceId()) {
  return request(`/llm/settings${queryString({ workspace_id: workspaceId })}`);
}

export function saveLLMSettings(data) {
  return request("/llm/settings", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function updateLLMSettings(settingsId, data) {
  return request(`/llm/settings/${settingsId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deleteLLMSettings(settingsId) {
  return request(`/llm/settings/${settingsId}`, { method: "DELETE" });
}

export function getPromptTemplates(workspaceId = getSelectedWorkspaceId()) {
  return request(`/llm/prompts${queryString({ workspace_id: workspaceId })}`);
}

export function createPromptTemplate(data) {
  return request("/llm/prompts", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function updatePromptTemplate(templateId, data) {
  return request(`/llm/prompts/${templateId}`, { method: "PUT", body: JSON.stringify(data) });
}

export function deletePromptTemplate(templateId) {
  return request(`/llm/prompts/${templateId}`, { method: "DELETE" });
}

export function runHybridReasoning(data) {
  return request("/llm/reason", { method: "POST", body: JSON.stringify({ ...data, workspace_id: data.workspace_id || getSelectedWorkspaceId() }) });
}

export function getReasoningTraces(workspaceId = getSelectedWorkspaceId()) {
  return request(`/llm/traces${queryString({ workspace_id: workspaceId })}`);
}

export function getReasoningTrace(traceId) {
  return request(`/llm/traces/${traceId}`);
}

export function getHybridResults(workspaceId = getSelectedWorkspaceId()) {
  return request(`/llm/hybrid-results${queryString({ workspace_id: workspaceId })}`);
}

export function getHybridResult(resultId) {
  return request(`/llm/hybrid-results/${resultId}`);
}

export function updateHybridApproval(resultId, data) {
  return request(`/llm/hybrid-results/${resultId}/approval`, { method: "PUT", body: JSON.stringify(data) });
}

export function exportReasoningTraceMarkdown(traceId) {
  return downloadReport(`/llm/traces/${traceId}/export-markdown`, `driftguard-reasoning-trace-${traceId.slice(0, 8)}.md`);
}
