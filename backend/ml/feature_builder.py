SOURCE_FIELDS = ["documentation", "code", "jira", "commit", "logs", "database_config", "question", "context"]


def build_input_text(record: dict) -> str:
    input_payload = record.get("input", record)
    sections = [
        ("Documentation", input_payload.get("documentation", "")),
        ("Code", input_payload.get("code", "")),
        ("Jira", input_payload.get("jira", "")),
        ("Commit", input_payload.get("commit", "")),
        ("Logs", input_payload.get("logs", "")),
        ("Config", input_payload.get("database_config", "")),
        ("Question", input_payload.get("question", "")),
        ("Context", input_payload.get("context", "")),
    ]
    return "\n".join(f"{title}:\n{value}" for title, value in sections if str(value).strip())


def create_vectorizer():
    from sklearn.feature_extraction.text import TfidfVectorizer

    return TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
