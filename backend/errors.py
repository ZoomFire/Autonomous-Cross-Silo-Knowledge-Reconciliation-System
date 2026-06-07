def api_error(message: str, status_code: int = 400, details: dict | None = None):
    return {
        "error": True,
        "message": message,
        "details": details or {},
        "status_code": status_code,
    }

