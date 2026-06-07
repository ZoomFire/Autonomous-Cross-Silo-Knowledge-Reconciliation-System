SUPPORTED_BENCHMARK_DATASETS = {
    "cosqa": {
        "name": "CosQA",
        "purpose": "Code-text alignment",
        "expected_formats": [".json", ".jsonl", ".csv"],
        "output_task": "code_text_alignment",
        "recommended_use": "Match natural language requirements or docs against code snippets.",
    },
    "snli": {
        "name": "SNLI",
        "purpose": "Contradiction detection",
        "expected_formats": [".jsonl", ".json", ".txt"],
        "output_task": "contradiction_detection",
        "recommended_use": "Teach contradiction, entailment, and neutral statement relationships.",
    },
    "commitpack": {
        "name": "CommitPack",
        "purpose": "Commit-code change reasoning",
        "expected_formats": [".json", ".jsonl", ".csv"],
        "output_task": "commit_drift_reasoning",
        "recommended_use": "Reason about whether commits or diffs may introduce drift.",
    },
    "spider": {
        "name": "Spider",
        "purpose": "Text-to-SQL / database reasoning",
        "expected_formats": [".json"],
        "output_task": "database_config_reasoning",
        "recommended_use": "Prepare future database and configuration reasoning examples.",
    },
    "custom": {
        "name": "Custom",
        "purpose": "DriftGuard-compatible case upload",
        "expected_formats": [".json", ".jsonl"],
        "output_task": "custom_driftguard_cases",
        "recommended_use": "Import cases that already follow the DriftGuard case schema.",
    },
}


def get_supported_benchmark_datasets() -> dict:
    return SUPPORTED_BENCHMARK_DATASETS
