from collections import Counter
from datetime import date
from pharos.corpus import digest


def measure(count, denominator, population="eligible_works"):
    return {"count": count, "denominator": denominator, "population": population,
            "percentage": round(count * 100 / denominator, 6) if denominator else None}


def distribution(counts, total, population, names=None):
    return [{"id": key, "label": (names or {}).get(key, key), **measure(value, total, population)}
            for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def calculate(observations, spec, identity, backend):
    rows = list(observations)
    ids = [r.id for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate canonical work IDs; population cannot be counted safely.")
    n = len(rows)
    start, end = int(spec["period"]["from"][:4]), int(spec["period"]["to"][:4])
    for row in rows:
        if not spec["period"]["from"] <= row.date <= spec["period"]["to"] or row.year != int(row.date[:4]):
            raise ValueError("Source publication date/year falls outside the saved corpus or is inconsistent.")
    current = int(backend["retrieved_at"][:4])
    annual = Counter(r.year for r in rows)
    fields = Counter(r.field_id for r in rows if r.field_id)
    classified = sum(fields.values())
    authorships = sum(r.authorships for r in rows)
    observable = sum(r.affiliation_observable for r in rows)
    institutions, names, countries = Counter(), {}, Counter()
    for row in rows:
        for identifier, name in row.institutions:
            if identifier != spec["resolved_openalex_id"]:
                institutions[identifier] += 1
                names[identifier] = name
        countries.update(row.countries)
    coverage = {
        "doi": measure(sum(bool(r.doi) for r in rows), n),
        "primary_subject": measure(classified, n),
        "authorships": measure(sum(r.authorships > 0 for r in rows), n),
        "affiliation_observable": measure(observable, n),
        "resolved_authorships": measure(sum(r.resolved_authorships for r in rows), authorships, "observed_authorships"),
        "unresolved_authorships": measure(sum(r.authorships - r.resolved_authorships for r in rows), authorships, "observed_authorships"),
        "abstracts": measure(sum(r.has_abstract for r in rows), n),
        "oa_information": measure(sum(r.is_oa is not None for r in rows), n),
        "oa_status": measure(sum(bool(r.oa_status) for r in rows), n),
        "repository_information": measure(sum(r.repository_copy is not None for r in rows), n),
        "funding_links": measure(sum(r.funding_linked for r in rows), n),
        "primary_source": measure(sum(bool(r.source_id) for r in rows), n),
        "work_type": measure(sum(bool(r.work_type) for r in rows), n),
        "retraction_information": measure(sum(r.retracted is not None for r in rows), n),
    }
    warnings = ["Missing metadata is unknown, not negative evidence.",
                "Live API retrieval is not an atomic snapshot. Frozen cached records support exact local reconstruction.",
                "Direct institution assignment only; organisational hierarchy is not expanded.",
                "Collaboration is whole-count shared-work co-occurrence, not partnership strength or impact. Countries include the home country.",
                "OpenAlex OA assertions do not independently establish legal reuse rights.",
                "Absent funder or award links do not establish absence of funding.",
                "Subject shares use classified works; rounded to six decimals."]
    if end >= current: warnings.append("The current year is incomplete; its count is excluded from complete-year extrema.")
    if any(r.authorships_truncated for r in rows):
        warnings.append("Some works have 100 observed authorships; API truncation may omit affiliations and collaborators.")
    complete = [annual[y] for y in range(start, end + 1) if y < current]
    return {"schema_version": "1.0", "profile_specification": "pharos-profile-v1", "corpus_specification_hash": digest(spec),
        "corpus": spec, "identity": identity, "backend": backend,
        "population": {"eligible_works": n, "classified_works": classified, "unclassified_works": n - classified,
                       "affiliation_observable_works": observable, "observed_authorships": authorships},
        "annual_counts": [{"year": y, **measure(annual[y], n), "complete_year": y < current} for y in range(start, end + 1)],
        "observed_years": {"first": min(annual) if annual else None, "last": max(annual) if annual else None,
                           "complete_year_minimum": min(complete) if complete else None,
                           "complete_year_maximum": max(complete) if complete else None},
        "retracted_works": measure(sum(r.retracted is True for r in rows), n),
        "work_type_distribution": distribution(Counter(r.work_type or "unknown" for r in rows), n, "eligible_works"),
        "subject_distribution": distribution(fields, classified, "classified_works", {r.field_id: r.field_name for r in rows if r.field_id}),
        "open_access": measure(sum(r.is_oa is True for r in rows), n),
        "open_access_distribution": distribution(Counter(r.oa_status or "unknown" for r in rows), n, "eligible_works"),
        "repository_copies": measure(sum(r.repository_copy is True for r in rows), n),
        "publication_sources": distribution(Counter(r.source_id for r in rows if r.source_id), n, "eligible_works", {r.source_id: f"{r.source_name} ({r.source_type or 'unknown'})" for r in rows}),
        "collaborators": distribution(institutions, n, "eligible_works", names),
        "collaboration_countries": distribution(countries, n, "eligible_works"), "coverage": coverage,
        "unresolved_submitted_identifiers": [], "warnings": warnings,
        "narrative": [{"text": f"OpenAlex records {n:,} eligible works in the selected corpus.", "field": "population.eligible_works"},
                      {"text": f"{classified:,} eligible works have a usable primary Field.", "field": "population.classified_works"}]}
