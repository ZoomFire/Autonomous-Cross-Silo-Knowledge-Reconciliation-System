from abc import ABC, abstractmethod


class BaseConnector(ABC):
    def __init__(self, config: dict):
        self.config = config or {}

    @abstractmethod
    def test_connection(self) -> dict:
        """Return a small status payload proving the connector can be reached."""

    @abstractmethod
    def sync(self) -> dict:
        """Return normalized sources plus import counters and errors."""

    def normalize_sources(self, sources: list[dict]) -> list[dict]:
        return sources

