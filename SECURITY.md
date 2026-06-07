# DriftGuard AI Security Notes

DriftGuard AI is an MVP-oriented local and Docker deployment. It includes authentication, workspaces, role-based access control, audit logging, observability, rate limiting, privacy controls, and basic HTTP security headers.

## Password Policy

New passwords must be at least 8 characters and include at least one letter and one number. Weak password attempts are rejected and logged as security audit events.

## Account Lockout

After 5 failed login attempts, the account is temporarily locked for 15 minutes. Failed logins and lockouts are recorded in the audit trail.

## Password Hashing

DriftGuard prefers `passlib[bcrypt]` for new password hashes. If bcrypt is unavailable or incompatible in the local environment, it safely falls back to the existing salted SHA256 implementation so local auth does not fail closed during development.

## Session Security

Sessions have expiry enforcement. Users can list their active sessions with masked tokens and revoke sessions from the Security dashboard.

Current limitation: local session storage still stores raw session tokens. Use stronger token hashing and managed session storage for production.

## Rate Limiting

The backend includes an in-memory rate limiter for login, signup, RAG search, agent runs, and uploads. This is suitable for local and demo usage.

Current limitation: in-memory limits reset on process restart and do not coordinate across multiple backend replicas.

## Secrets Masking

Connector configs and audit metadata mask common secrets such as API keys, tokens, passwords, and access keys before returning API responses.

## Sensitive Data Redaction

DriftGuard detects simple sensitive-data patterns including GitHub tokens, bearer tokens, passwords, secrets, private keys, email addresses, phone numbers, and database URLs. Privacy mode redacts sensitive values in previews and exports.

## Privacy Mode

Each workspace has privacy settings for privacy mode, export redaction, data retention days, workspace export, and delete request controls.

## Workspace Data Export

Admins can export workspace data as JSON. If export redaction is enabled, sensitive values are redacted in the exported file.

## Delete Request Workflow

Admins can create workspace deletion requests and approve them. Level 3.8 approval does not physically delete data; physical deletion remains a separate workspace admin action.

## SQLite Local Storage

SQLite is the default database and works well for local deployment. For multi-user production deployments, use PostgreSQL or another managed relational database.

## Optional LLM API Keys

Optional LLM API keys should never be committed. Use runtime-only keys for MVP use, and a real secrets manager for production.

## HTTPS

Use HTTPS in production. Put DriftGuard behind a reverse proxy or load balancer that terminates TLS.

## Secrets Management

Do not store production secrets in `.env` files committed to source control. Use a cloud secrets manager, Docker secrets, or your platform's secure environment variable storage.

## Production Database

Use PostgreSQL for multi-user production deployments, backups, and better operational controls.

## Security Headers

The backend sets basic headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`

Review and expand these headers for your production hosting environment.
