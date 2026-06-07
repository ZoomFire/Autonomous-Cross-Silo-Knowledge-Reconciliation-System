from pathlib import Path

from .base import BaseConnector
from .source_normalizer import csv_to_text, json_to_text, normalize_imported_source


class FileConnector(BaseConnector):
    def test_connection(self) -> dict:
        files = self.config.get("files", [])
        return {"status": "ok", "message": f"{len(files)} uploaded file(s) ready to import."}

    def sync(self) -> dict:
        imported = []
        skipped = 0
        errors = []
        connector_type = self.config.get("connector_type", "manual_upload")

        for item in self.config.get("files", []):
            filename = item.get("filename", "uploaded-source.txt")
            raw_content = item.get("content", b"")
            extension = Path(filename).suffix.lower()
            try:
                if extension == ".csv":
                    content = csv_to_text(raw_content)
                elif extension == ".json":
                    content = json_to_text(raw_content)
                else:
                    content = raw_content
                imported.append(normalize_imported_source(filename, content, connector_type))
            except Exception as exc:
                skipped += 1
                errors.append({"file": filename, "error": str(exc)})

        return {
            "sources": imported,
            "files_imported": len(imported),
            "files_skipped": skipped,
            "errors": errors,
            "summary": f"Imported {len(imported)} uploaded source file(s).",
        }

