from database.repositories import DeployedModelRepository, EvaluationRepository


def compare_baselines(workspace_id: str, dataset_id: str) -> dict:
    evaluations = [item for item in EvaluationRepository.list(workspace_id) if item.get("dataset_id") == dataset_id]
    latest = evaluations[0] if evaluations else {}
    rule_accuracy = latest.get("accuracy", 0)
    results = [{"mode": "rule_based", "accuracy": rule_accuracy, "f1_macro": 0, "notes": "Local rule-based engine"}]
    deployed = DeployedModelRepository.list_by_workspace(workspace_id)
    if deployed:
        results.append({"mode": "deployed_ml", "accuracy": 0, "f1_macro": 0, "notes": "Deployed ML exists, but validation dataset prediction scoring is not wired in this MVP."})
    else:
        results.append({"mode": "deployed_ml", "accuracy": 0, "f1_macro": 0, "notes": "No deployed ML model available."})
    best = max(results, key=lambda item: item.get("accuracy", 0))
    return {"baseline_results": results, "best_mode": best["mode"], "summary": f"{best['mode']} produced the highest available accuracy. ML/hybrid comparison is best-effort in this MVP."}
