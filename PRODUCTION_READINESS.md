# Production Readiness

## Level 3.7 Observability

- Observability has been added for request metrics, slow endpoint tracking, error events, and admin-only performance health checks.
- Current limitation: local JSON metrics are an MVP storage layer and are intended for small deployments or local QA.
- Future upgrade: Prometheus, Grafana, or OpenTelemetry should replace local JSON files for higher-volume production deployments.

## Level 3.8 Security and Privacy

- For production, use managed secrets rather than local `.env` files or plaintext connector configs.
- Use HTTPS behind a trusted reverse proxy or load balancer.
- Use stronger session management with hashed tokens, rotation, secure cookies where appropriate, and centralized revocation.
- Use PostgreSQL instead of SQLite for multi-user production deployments.
- Use Redis-backed or gateway-backed rate limiting for multi-instance deployments.
- Use encrypted storage for secrets and sensitive connector configuration.

## Level 4.0 Model Training Sandbox

- ML training is local baseline only and is intended for safe experimentation with TF-IDF and classical scikit-learn models.
- No GPU is required, and no paid APIs or external model providers are used.
- Keep the rule-based engine available as the production fallback when no local model is deployed or when a rollback is needed.
- For production MLOps, use a real model registry, model versioning, approval gates, scheduled evaluation, and artifact retention policies.
- Evaluate training data quality, fairness, class balance, and domain coverage before deploying any trained model into operational workflows.

## Level 4.4 Incident Management

- Incident lifecycle data, comments, timelines, webhooks, delivery logs, and escalation rules are stored in SQLite for local MVP use.
- Webhook delivery is best-effort and non-blocking; failed deliveries are captured in notification logs.
- For production, move escalation checks to a scheduler or queue worker instead of relying only on manual API calls.
- Validate webhook destinations against an allowlist, sign webhook payloads, and store secrets in managed secret storage.
- Add retention policies for incident comments, timeline events, and notification logs before regulated deployments.
- Use PostgreSQL and background workers for multi-user, high-volume production incident operations.

## Level 4.5 External Workflow Integrations

- Mock integrations are demo-ready and require no external API keys.
- For production, configure real Jira, GitHub, Slack, Teams, or webhook APIs only through approved integration settings.
- Store external API tokens, webhook secrets, and passwords using a secure secret manager rather than SQLite config fields.
- Add an allowlist for live webhook destinations and audit reviews for every enabled live integration.
- Add a retry queue, backoff, and dead-letter handling for failed external ticket/notification syncs.
- Monitor sync failure rates and alert when external workflow automations are degraded.

## Level 4.6 Executive Reporting and Demo Mode

- Executive metrics are MVP estimates derived from local DriftGuard data and should be validated before contractual or financial use.
- ROI is based on configurable assumptions such as review time, hourly cost, and incident impact.
- For production, connect financial, ticketing, and business impact data sources to replace estimated values.
- Demo mode should remain clearly labeled in production-like environments.
- Demo reset intentionally avoids deleting user accounts or normal workspace data.

## Level 4.7 Validation and Research Results

- Validation metrics are based on local MVP data and should be treated as research/demo evidence, not certified production benchmarks.
- For production, integrate continuous validation pipelines, external benchmark suites, scheduled regression checks, and statistical significance tracking.
- Baseline comparison and ablation studies use best-effort local outputs unless full ML/hybrid scoring is configured.
- Store validation history with retention policies before large-scale enterprise usage.
