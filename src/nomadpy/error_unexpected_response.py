class UnexpectedResponseError(Exception):
    """UnexpectedResponseError is raised when the server answers with a status code the caller did not expect."""

    def __init__(self, status_code: int, status_text: str = "", body: str = "", expected: tuple[int, ...] = ()):
        self.status_code = status_code
        self.status_text = status_text or "unknown status code"
        self.body = body
        self.expected = expected
        super().__init__(str(self))

    def __str__(self) -> str:
        text = f"Unexpected response code: {self.status_code}"
        if self.body:
            text += f" ({self.body})"
        return text
