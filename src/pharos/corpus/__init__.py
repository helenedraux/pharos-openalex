import hashlib
import json
import re
from datetime import date


def selector(value):
    original = value
    value = value.strip().rstrip("/")
    if re.fullmatch(r"(?:https://openalex.org/)?I[1-9][0-9]*", value, re.I):
        return {"type": "institution", "id_namespace": "openalex", "id": value.split("/")[-1].upper(), "original": original}
    value = re.sub(r"^https?://ror.org/", "", value)
    if re.fullmatch(r"0[0-9a-hj-km-np-tv-z]{6}[0-9]{2}", value):
        return {"type": "institution", "id_namespace": "ror", "id": "https://ror.org/" + value, "original": original}
    raise ValueError("Supply a ROR or OpenAlex institution ID. Name resolution is not supported; no identity was selected.")


def specification(selected, institution_id, start, end):
    if not 1 <= start <= end <= date.today().year:
        raise ValueError("Years must be ordered and between 1 and the current year.")
    return {"schema_version": "1.0", "selector": selected, "resolved_openalex_id": institution_id,
            "period": {"from": f"{start:04d}-01-01", "to": f"{end:04d}-12-31"},
            "entity_projection": "direct", "work_types": "all", "manifestation_policy": "pharos-observed-works-v1",
            "retractions": "retain_and_flag", "openalex_corpus": "core", "counting_method": "whole",
            "profile_specification": "pharos-profile-v1"}


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
