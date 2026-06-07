from models import DatasetCase


COMPONENT_KEYWORDS = {
    "payment": ["payment", "refund", "transaction"],
    "authentication": ["login", "auth", "jwt", "session", "token"],
    "user": ["user", "profile", "account"],
    "order": ["order", "cart", "checkout"],
    "inventory": ["inventory", "product", "stock"],
    "notification": ["notification", "email", "sms"],
    "platform": ["config", "database", "feature flag", "feature_enabled"],
}

SOURCE_TO_FIELD = {
    "documentation": "documentation",
    "code": "code",
    "jira": "jira",
    "logs": "logs",
    "database_config": "database_config",
    "commit": "commit",
}


def _component_for_source(source: dict) -> str:
    haystack = " ".join([
        source.get("source_name", ""),
        source.get("source_path", ""),
        source.get("content_text", "")[:3000],
    ]).lower()
    for component, keywords in COMPONENT_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return component
    return "general"


def _append_field(case: dict, field: str, source: dict):
    header = f"[{source.get('source_name', 'source')}]"
    content = source.get("content_text", "")
    if not content:
        return
    case[field] = "\n\n".join(part for part in [case.get(field, ""), f"{header}\n{content[:6000]}"] if part)


def build_dataset_cases_from_sources(sources: list[dict]) -> list[DatasetCase]:
    groups: dict[str, list[dict]] = {}
    for source in sources:
        groups.setdefault(_component_for_source(source), []).append(source)

    cases: list[DatasetCase] = []
    for index, (component, items) in enumerate(sorted(groups.items()), start=1):
        case = {
            "case_id": f"AUTO-{index:03d}",
            "title": f"Auto-generated drift case for {component}",
            "documentation": "",
            "code": "",
            "jira": "",
            "commit": "",
            "logs": "",
            "database_config": "",
            "expected_label": "uncertain",
            "expected_drift_type": "Unknown",
            "expected_severity": "Medium",
        }
        for source in items:
            field = SOURCE_TO_FIELD.get(source.get("source_type", "unknown"))
            if field:
                _append_field(case, field, source)
        cases.append(DatasetCase(**case))

    return cases
