import re
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .base import BaseConnector
from .source_normalizer import CODE_EXTENSIONS, CONFIG_EXTENSIONS, DOC_EXTENSIONS, normalize_imported_source


DEFAULT_EXCLUDE_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv", "target", "coverage"}
SUPPORTED_EXTENSIONS = CODE_EXTENSIONS | DOC_EXTENSIONS | CONFIG_EXTENSIONS
MAX_FILE_SIZE = 1024 * 1024


def _parse_github_repo_url(repo_url: str) -> tuple[str, str]:
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/#?]+)", repo_url.strip())
    if not match:
        raise ValueError("Please enter a valid GitHub repository URL.")
    return match.group("owner"), match.group("repo").removesuffix(".git")


class GitHubConnector(BaseConnector):
    def _zip_url(self) -> str:
        owner, repo = _parse_github_repo_url(self.config.get("repo_url", ""))
        branch = self.config.get("branch") or "main"
        return f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

    def test_connection(self) -> dict:
        zip_url = self._zip_url()
        request = urllib.request.Request(zip_url, method="HEAD")
        token = self.config.get("access_token")
        if token:
            request.add_header("Authorization", f"token {token}")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return {"status": "ok", "message": f"Repository is reachable. HTTP {response.status}."}
        except Exception as exc:
            raise ValueError(f"GitHub repository could not be reached: {exc}") from exc

    def sync(self) -> dict:
        include_extensions = set(self.config.get("include_extensions") or SUPPORTED_EXTENSIONS)
        exclude_dirs = set(self.config.get("exclude_dirs") or DEFAULT_EXCLUDE_DIRS)
        repo_url = self.config.get("repo_url", "")
        errors = []
        imported = []
        skipped = 0

        request = urllib.request.Request(self._zip_url())
        token = self.config.get("access_token")
        if token:
            request.add_header("Authorization", f"token {token}")

        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "repo.zip"
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    zip_path.write_bytes(response.read())
            except Exception as exc:
                raise ValueError(f"GitHub repository download failed: {exc}") from exc

            try:
                with zipfile.ZipFile(zip_path) as archive:
                    archive.extractall(Path(temp_dir) / "repo")
            except zipfile.BadZipFile as exc:
                raise ValueError("Downloaded repository archive was not a valid ZIP file.") from exc

            root = Path(temp_dir) / "repo"
            for file_path in root.rglob("*"):
                if not file_path.is_file():
                    continue
                relative_parts = file_path.relative_to(root).parts
                if any(part in exclude_dirs for part in relative_parts):
                    skipped += 1
                    continue
                if file_path.suffix.lower() not in include_extensions:
                    skipped += 1
                    continue
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    skipped += 1
                    continue
                try:
                    relative_path = "/".join(relative_parts[1:]) if len(relative_parts) > 1 else file_path.name
                    imported.append(normalize_imported_source(relative_path, file_path.read_bytes(), "github", repo_url))
                except Exception as exc:
                    skipped += 1
                    errors.append({"file": str(file_path), "error": str(exc)})

        return {
            "sources": imported,
            "files_imported": len(imported),
            "files_skipped": skipped,
            "errors": errors,
            "summary": f"Imported {len(imported)} file(s) from GitHub repository.",
        }

