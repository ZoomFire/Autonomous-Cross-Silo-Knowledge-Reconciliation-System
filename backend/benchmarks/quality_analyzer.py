from collections import Counter


CODE_RELATED_TYPES = {"cosqa", "commitpack"}


def _case(example: dict) -> dict:
    return example.get("driftguard_case") or example.get("driftguard_case_json") or {}


def score_example(example: dict) -> int:
    case = _case(example)
    dataset_type = example.get("dataset_type", "")
    score = 100
    if not (case.get("documentation") or case.get("jira") or case.get("commit") or case.get("database_config")):
        score -= 10
    if dataset_type in CODE_RELATED_TYPES and not case.get("code"):
        score -= 10
    if case.get("expected_label") == "uncertain":
        score -= 15
    target = example.get("target", {})
    if not target.get("explanation"):
        score -= 10
    return max(0, score)


def analyze_benchmark_quality(examples: list[dict]) -> dict:
    dataset_types = Counter()
    labels = Counter()
    drift_types = Counter()
    severities = Counter()
    splits = Counter()
    missing = Counter()
    scores = []
    for example in examples:
        case = _case(example)
        target = example.get("target", {})
        dataset_types[example.get("dataset_type", "unknown")] += 1
        labels[target.get("label") or case.get("expected_label") or "unknown"] += 1
        drift_types[target.get("drift_type") or case.get("expected_drift_type") or "unknown"] += 1
        severities[target.get("severity") or case.get("expected_severity") or "unknown"] += 1
        splits[example.get("split", "unsplit")] += 1
        for field in ["documentation", "code", "jira", "commit", "database_config"]:
            if not case.get(field):
                missing[field] += 1
        score = example.get("quality_score") or score_example(example)
        scores.append(score)

    average = round(sum(scores) / len(scores), 2) if scores else 0
    warnings = []
    if labels.get("uncertain", 0) > max(3, len(examples) * 0.5):
        warnings.append("Many examples have uncertain labels.")
    if splits.get("unsplit", 0):
        warnings.append("Some examples are not assigned to train, validation, or test.")
    recommendations = []
    if average < 75:
        recommendations.append("Review low-scoring examples before exporting training data.")
    if not splits or splits.get("unsplit", 0):
        recommendations.append("Create a deterministic train/validation/test split.")
    return {
        "total_examples": len(examples),
        "dataset_type_distribution": dict(dataset_types),
        "label_distribution": dict(labels),
        "drift_type_distribution": dict(drift_types),
        "severity_distribution": dict(severities),
        "split_distribution": dict(splits),
        "average_quality_score": average,
        "missing_field_counts": dict(missing),
        "warnings": warnings,
        "recommendations": recommendations or ["Dataset quality looks ready for export."],
    }
