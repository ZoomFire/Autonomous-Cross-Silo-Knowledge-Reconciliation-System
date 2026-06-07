def evaluate_model(y_true, y_pred, labels=None) -> dict:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support

    labels = labels or sorted(set(y_true) | set(y_pred))
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(float(precision), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
        "classification_report": classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0),
        "confusion_matrix": {
            "labels": labels,
            "matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        },
    }

