class DomainError(Exception):
    """Messages here are safe to show to users; provider/SQL exceptions are not."""

    def __init__(self, message: str, status_code: int = 400, retry_after: int | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class GenerationUnavailable(DomainError):
    def __init__(self):
        super().__init__('Не удалось составить микс. Попробуйте позже.', 503)
