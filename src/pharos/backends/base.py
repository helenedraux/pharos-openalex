from typing import Protocol
from pharos.contracts import Observation

class ObservationBackend(Protocol):
    """Future adapters must yield these observations, independent of source schema."""
    def observations(self) -> list[Observation]: ...
