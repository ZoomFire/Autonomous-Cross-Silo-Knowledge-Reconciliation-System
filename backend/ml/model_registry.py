import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from config import STORAGE_DIR


MODELS_DIR = STORAGE_DIR / "models"
ARTIFACTS_DIR = MODELS_DIR / "artifacts"
LOGS_DIR = MODELS_DIR / "logs"


def ensure_model_dirs():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_model_artifact(workspace_id: str, experiment_id: str, model, vectorizer, metadata: dict) -> dict:
    import joblib

    ensure_model_dirs()
    artifact_dir = ARTIFACTS_DIR / workspace_id / experiment_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_path = artifact_dir / "model.joblib"
    vectorizer_path = artifact_dir / "vectorizer.joblib"
    metadata_path = artifact_dir / "metadata.json"
    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    metadata = {"created_at": _now(), **metadata}
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {
        "model_path": str(model_path),
        "vectorizer_path": str(vectorizer_path),
        "metadata_path": str(metadata_path),
        "metadata": metadata,
    }


def load_model_artifact(artifact: dict) -> tuple[object, object, dict]:
    import joblib

    model = joblib.load(artifact["model_path"])
    vectorizer = joblib.load(artifact["vectorizer_path"])
    metadata = get_model_metadata(artifact)
    return model, vectorizer, metadata


def get_model_metadata(artifact: dict) -> dict:
    path = Path(artifact.get("metadata_path", ""))
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def list_model_artifacts(workspace_id: str) -> list[dict]:
    ensure_model_dirs()
    workspace_dir = ARTIFACTS_DIR / workspace_id
    if not workspace_dir.exists():
        return []
    return [{"experiment_id": path.name, "path": str(path)} for path in workspace_dir.iterdir() if path.is_dir()]


def delete_model_artifact(artifact: dict) -> bool:
    model_path = Path(artifact.get("model_path", ""))
    artifact_dir = model_path.parent if model_path else None
    if artifact_dir and artifact_dir.exists() and ARTIFACTS_DIR in artifact_dir.parents:
        shutil.rmtree(artifact_dir)
        return True
    return False

