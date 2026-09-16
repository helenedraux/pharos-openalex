# Multi-use readiness and interoperability plan

## Product model

Pharos distinguishes five things:

1. A **view** is the interactive evidence about one OpenAlex object.
2. A **snapshot** is the dated aggregate evidence for an explicit scope and period.
3. A **review** tests that snapshot against one or more intended uses.
4. A **report** communicates the use-specific results, limitations, and methodology.
5. A **data package** carries the supporting data, identifiers, scope, and provenance.

## Decision model

Users may select several intended uses. Pharos presents evidence once and maps it to every selected use. It does not average unrelated evidence into a quality score.

Each use receives one readiness category:

- **Ready**: every essential requirement is met.
- **Ready with limitations**: essential requirements are met, but relevant evidence is incomplete or below its configured requirement.
- **Validation needed**: an essential requirement needs local, record-level, policy, or destination-system evidence.
- **Not supported by this snapshot**: an essential configured requirement is not met.

Initial results are deterministic and provisional. Users may change a threshold or materiality only with a recorded reason and rationale. Case-level claims cannot pass automatically from aggregate OpenAlex evidence.

## Interoperability

Every evidence requirement states whether OpenAlex is sufficient, which authoritative source should be joined, and what validation remains. Typical joins include a CRIS or repository, HR and organisation records, award or finance systems, ORCID/ROR/Crossref identifiers, publication full text, and funder policy definitions.

Interoperability is part of readiness, not a footer. Automatic schema checks are kept separate from destination-specific mappings, test imports, deduplication, and round trips.

## Benchmarks

Benchmarks provide context, not compliance decisions. Pharos will only label a measure benchmarkable when a like-for-like comparator can use the same period, work types, population definition, and relevant field or geography. Until comparator data is calculated, the interface says that no benchmark is available; it never fabricates a national or global value.

Recorded acknowledgement prevalence, open-access availability, ORCID presence, and similar measures must not be described as proof of real-world compliance or completeness.

## Delivery sequence

1. Multi-select intended uses and display a deduplicated evidence-by-use matrix.
2. Add deterministic provisional readiness and transparent threshold metadata.
3. Bring source-of-truth and required-join information into every evidence row.
4. Preserve the detailed review for recording statuses, evidence, overrides, and notes.
5. Export a versioned combined review record and a human-readable report.
6. Add calculated peer benchmarks only after population matching and provenance are implemented.
