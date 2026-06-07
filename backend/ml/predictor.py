from database.repositories import DeployedModelRepository, ModelArtifactRepository
from .feature_builder import build_input_text
from .model_registry import load_model_artifact


def predict_with_active_model(workspace_id: str, task_type: str, input_context: dict) -> dict:
    deployed = DeployedModelRepository.get_active_model_for_task(workspace_id, task_type)
    if not deployed:
        return {
            "task_type": task_type,
            "fallback_required": True,
            "fallback_used": True,
            "message": "No deployed model found. Use rule-based engine fallback.",
        }
    artifact = ModelArtifactRepository.get_by_id(deployed.get("artifact_id", ""))
    if not artifact:
        return {
            "task_type": task_type,
            "fallback_required": True,
            "fallback_used": True,
            "message": "Deployed artifact is missing. Use rule-based engine fallback.",
        }
    model, vectorizer, _metadata = load_model_artifact(artifact)
    text = build_input_text({"input": input_context})
    prediction = model.predict(vectorizer.transform([text]))[0]
    confidence = None
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(vectorizer.transform([text]))[0]
        confidence = round(float(max(probabilities)), 4)
    return {
        "task_type": task_type,
        "prediction": str(prediction),
        "confidence": confidence,
        "model_type": deployed.get("model_type", ""),
        "experiment_id": deployed.get("experiment_id", ""),
        "fallback_used": False,
        "fallback_required": False,
    }
