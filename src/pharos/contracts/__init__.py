"""Backend-independent observations. Raw source assertions remain in the checkpoint."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Observation:
    id: str
    doi: str | None
    pmid: str | None
    date: str
    year: int
    work_type: str | None
    field_id: str | None
    field_name: str | None
    is_oa: bool | None
    oa_status: str | None
    repository_copy: bool | None
    authorships: int
    resolved_authorships: int
    affiliation_observable: bool
    institutions: tuple[tuple[str, str], ...]
    countries: tuple[str, ...]
    has_abstract: bool
    funding_linked: bool
    retracted: bool | None
    source_id: str | None
    source_name: str | None
    source_type: str | None
    authorships_truncated: bool
