from __future__ import annotations


class HttpRequestError(RuntimeError):
    """Represents an HTTP request failure with structured context."""

    def __init__(
        self,
        source: str,
        status_code: int,
        details: str,
        url: str | None = None,
    ):
        self.source = source
        self.status_code = status_code
        self.details = details
        self.url = url

        location = f" ({url})" if url else ""
        super().__init__(f"{source} HTTP {status_code}: {details}{location}")

    def to_context(self) -> dict[str, str]:
        return {
            "source": self.source,
            "status": str(self.status_code),
            "details": self.details,
            "url": self.url or "unknown",
            "error_type": type(self).__name__,
        }