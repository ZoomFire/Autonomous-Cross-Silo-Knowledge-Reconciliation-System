from collections import Counter

from . import SUPPORTED_MODEL_TYPES, SUPPORTED_TASK_TYPES
from .evaluator import evaluate_model
from .feature_builder import create_vectorizer
from .model_registry import save_model_artifact


TASK_TARGET_FIELD = {
    "label_classification": "label",
    "severity_classification": "severity",
    "drift_type_classification": "drift_type",
}


def _model_for(model_type: str, random_seed: int):
    if model_type == "logistic_regression":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(max_iter=1000)
    if model_type == "linear_svm":
        from sklearn.svm import LinearSVC
        return LinearSVC()
    if model_type == "naive_bayes":
        from sklearn.naive_bayes import MultinomialNB
        return MultinomialNB()
    if model_type == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=100, random_state=random_seed)
    raise ValueError("Invalid model_type.")


def train_model(workspace_id: str, experiment_id: str, task_type: str, model_type: str, examples: list[dict], test_size: float = 0.2, random_seed: int = 42) -> dict:
    from sklearn.model_selection import train_test_split

    if task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError("Invalid task_type.")
    if model_type not in SUPPORTED_MODEL_TYPES:
        raise ValueError("Invalid model_type.")
    target_field = TASK_TARGET_FIELD[task_type]
    labeled = [item for item in examples if item.get(target_field)]
    if len(labeled) < 10:
        raise ValueError("At least 10 labeled examples are required for training.")
    labels = sorted({item[target_field] for item in labeled})
    if len(labels) < 2:
        raise ValueError("Training requires at least two classes.")

    texts = [item["text"] for item in labeled]
    y = [item[target_field] for item in labeled]
    stratify = y if min(Counter(y).values()) >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(texts, y, test_size=test_size, random_state=random_seed, stratify=stratify)
    vectorizer = create_vectorizer()
    x_train_vec = vectorizer.fit_transform(x_train)
    x_test_vec = vectorizer.transform(x_test)
    model = _model_for(model_type, random_seed)
    model.fit(x_train_vec, y_train)
    y_pred = model.predict(x_test_vec)
    metrics = evaluate_model(y_test, y_pred, labels=labels)
    metadata = {
        "experiment_id": experiment_id,
        "workspace_id": workspace_id,
        "task_type": task_type,
        "model_type": model_type,
        "metrics": metrics,
        "labels": labels,
    }
    artifact = save_model_artifact(workspace_id, experiment_id, model, vectorizer, metadata)
    return {
        "metrics": metrics,
        "artifact": artifact,
        "labels": labels,
        "label_distribution": dict(Counter(y)),
        "train_count": len(y_train),
        "validation_count": 0,
        "test_count": len(y_test),
        "total_examples": len(labeled),
        "training_log": [
            f"Loaded {len(examples)} examples.",
            f"Used {len(labeled)} labeled examples for {task_type}.",
            f"Trained {model_type} with TF-IDF features.",
            f"Evaluation F1 macro: {metrics['f1_macro']}.",
        ],
    }

