import csv
import hashlib
import json
from pathlib import Path


CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".php", ".rb"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".html", ".htm"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".env", ".toml", ".ini"}
LOG_EXTENSIONS = {".log"}
JIRA_KEYS = ["issue", "ticket", "status", "assignee", "summary", "priority", "jira"]
CONFIG_KEYS = ["access_type", "visibility", "feature_enabled", "database", "config", "flag", "enabled", "secret"]


def clean_text(content: bytes | str) -> str:
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="ignore")
    else:
        text = content
    return text.replace("\x00", "").strip()


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _detected_language(extension: str) -> str:
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
    }.get(extension, "text")


def _looks_like_jira(filename: str, text: str) -> bool:
    lowered = f"{filename}\n{text[:2000]}".lower()
    if filename.lower().endswith(".csv"):
        try:
            first_line = text.splitlines()[0] if text.splitlines() else ""
            return any(key in first_line.lower() for key in JIRA_KEYS)
        except IndexError:
            return False
    return any(key in lowered for key in JIRA_KEYS)


def _looks_like_config(text: str) -> bool:
    lowered = text[:4000].lower()
    return any(key in lowered for key in CONFIG_KEYS)


def _looks_like_commit(text: str) -> bool:
    lowered = text[:2000].lower()
    return "commit" in lowered or "hash" in lowered or "changed" in lowered


def normalize_imported_source(filename: str, content: bytes | str, connector_type: str, source_url: str = "") -> dict:
    text = clean_text(content)
    path = Path(filename)
    extension = path.suffix.lower()
    source_type = "unknown"

    if connector_type == "logs" or extension in LOG_EXTENSIONS:
        source_type = "logs"
    elif connector_type == "jira" or _looks_like_jira(filename, text):
        source_type = "jira"
    elif extension in CODE_EXTENSIONS:
        source_type = "code"
    elif extension in CONFIG_EXTENSIONS and (connector_type == "config" or _looks_like_config(text)):
        source_type = "database_config"
    elif connector_type == "confluence" or extension in DOC_EXTENSIONS:
        source_type = "documentation"
    elif _looks_like_commit(text):
        source_type = "commit"

    return {
        "source_type": source_type,
        "source_name": path.name or filename,
        "source_path": filename,
        "source_url": source_url,
        "content_text": text,
        "content_hash": content_hash(text),
        "metadata": {
            "extension": extension,
            "size": len(text.encode("utf-8")),
            "detected_language": _detected_language(extension),
            "connector_type": connector_type,
        },
    }


def csv_to_text(content: bytes | str) -> str:
    text = clean_text(content)
    rows = []
    for row in csv.DictReader(text.splitlines()):
        rows.append("; ".join(f"{key}: {value}" for key, value in row.items() if value))
    return "\n".join(rows) if rows else text


def json_to_text(content: bytes | str) -> str:
    text = clean_text(content)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text
    return json.dumps(parsed, indent=2, ensure_ascii=False)

