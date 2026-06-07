import json
from urllib import request as url_request
from urllib.error import HTTPError, URLError


def post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 5) -> dict:
    try:
        encoded = json.dumps(payload).encode("utf-8")
        req = url_request.Request(url, data=encoded, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
        with url_request.urlopen(req, timeout=timeout) as response:
            text = response.read(2048).decode("utf-8", errors="replace")
            return {"success": 200 <= response.status < 300, "status_code": response.status, "text": text}
    except HTTPError as exc:
        return {"success": False, "status_code": exc.code, "text": exc.read(2048).decode("utf-8", errors="replace"), "error": str(exc)}
    except (URLError, TimeoutError, OSError) as exc:
        return {"success": False, "status_code": 0, "text": "", "error": str(exc)}
