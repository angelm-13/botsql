class AppError(Exception):
    def __init__(self, message_key: str, status_code: int = 400, meta: dict | None = None):
        super().__init__(message_key)
        self.message_key = message_key
        self.status_code = status_code
        self.meta = meta or {}
