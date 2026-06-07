from uuid import uuid4

from connector_store import utc_now
from database.repositories import PromptTemplateRepository


DEFAULT_TEMPLATES = [
    {
        "name": "Claim Extraction",
        "task_type": "claim_extraction",
        "template_text": "You are analyzing enterprise system knowledge sources.\nExtract precise claims from the following source:\nSource Type: {source_type}\nContent:\n{content}\n\nReturn JSON with claims.",
        "variables": ["source_type", "content"],
    },
    {
        "name": "Contradiction Detection",
        "task_type": "contradiction_detection",
        "template_text": "Compare the following documentation, code, Jira, logs, and config.\nIdentify contradictions and architectural drift.\nDocumentation:\n{documentation}\nCode:\n{code}\nJira:\n{jira}\nLogs:\n{logs}\nConfig:\n{database_config}\n\nReturn JSON with label, drift_type, severity, evidence, explanation.",
        "variables": ["documentation", "code", "jira", "logs", "database_config"],
    },
    {
        "name": "Root Cause Analysis",
        "task_type": "root_cause_analysis",
        "template_text": "Analyze the drift evidence and identify root cause, responsible source, recommended fix, and priority.\nEvidence:\n{evidence}\n\nReturn JSON.",
        "variables": ["evidence"],
    },
    {
        "name": "Fix Recommendation",
        "task_type": "fix_recommendation",
        "template_text": "Recommend a practical fix for this drift case.\nContext:\n{context}\n\nReturn JSON with recommended_fix, priority_level, and suggested_owner.",
        "variables": ["context"],
    },
    {
        "name": "Agent Report",
        "task_type": "agent_report",
        "template_text": "Create a concise drift investigation report for the goal: {goal}\nWorkflow outputs:\n{step_outputs}\n\nReturn JSON with executive_summary, risk_level, and recommended_actions.",
        "variables": ["goal", "step_outputs"],
    },
]


def get_default_prompt_templates() -> list[dict]:
    return DEFAULT_TEMPLATES


def render_prompt(template_text: str, variables: dict) -> str:
    class SafeVariables(dict):
        def __missing__(self, key):
            return ""

    safe_variables = SafeVariables({key: str(value) for key, value in (variables or {}).items()})
    return template_text.format_map(safe_variables)


def list_prompt_templates(workspace_id: str) -> list[dict]:
    saved = PromptTemplateRepository.list_by_workspace(workspace_id)
    if saved:
        return saved
    return [
        {
            "template_id": f"default-{item['task_type']}",
            "workspace_id": workspace_id,
            "created_by": "system",
            "created_at": "",
            "updated_at": "",
            **item,
        }
        for item in DEFAULT_TEMPLATES
    ]


def get_prompt_template(template_id: str) -> dict | None:
    if template_id.startswith("default-"):
        task_type = template_id.replace("default-", "", 1)
        default = next((item for item in DEFAULT_TEMPLATES if item["task_type"] == task_type), None)
        return {"template_id": template_id, "workspace_id": "", "created_by": "system", "created_at": "", "updated_at": "", **default} if default else None
    return PromptTemplateRepository.get_by_id(template_id)


def create_prompt_template(payload: dict, user_id: str) -> dict:
    now = utc_now()
    return PromptTemplateRepository.create({
        "template_id": str(uuid4()),
        "workspace_id": payload.get("workspace_id", ""),
        "name": payload.get("name", "Untitled Prompt"),
        "task_type": payload.get("task_type", ""),
        "template_text": payload.get("template_text", ""),
        "variables": payload.get("variables", []),
        "created_by": user_id,
        "created_at": now,
        "updated_at": now,
    })


def update_prompt_template(template_id: str, payload: dict) -> dict | None:
    return PromptTemplateRepository.update(template_id, {**payload, "updated_at": utc_now()})


def ensure_default_prompt_templates(workspace_id: str = "__default__") -> list[dict]:
    existing = PromptTemplateRepository.list_by_workspace(workspace_id)
    if existing:
        return existing
    created = []
    now = utc_now()
    for item in DEFAULT_TEMPLATES:
        created.append(PromptTemplateRepository.create({
            "template_id": str(uuid4()),
            "workspace_id": workspace_id,
            "name": item["name"],
            "task_type": item["task_type"],
            "template_text": item["template_text"],
            "variables": item["variables"],
            "created_by": "system",
            "created_at": now,
            "updated_at": now,
        }))
    return created
