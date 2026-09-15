# Methodology and current API references

Verified 2026-09-07 against the official OpenAlex documentation:

- [Authentication](https://help.openalex.org/api/authentication/): bearer header authentication, up to 100 results per page, and HTTP 429 for rate/budget limits.
- [Example costs](https://help.openalex.org/access/example-costs/): $0.0001 per list/filter call; single-entity lookups free; $1 daily free-account budget; $0.10 anonymous daily budget.
- [Pricing](https://help.openalex.org/access/pricing/): free account route and billing policies.
- [Cursor pagination](https://help.openalex.org/api/paging/): follow `meta.next_cursor` to exhaustion.
- [Works attributes](https://help.openalex.org/data/works/attributes/): primary topics, OA assertions, authorships, funding, and retractions.
- [Corpus selection](https://help.openalex.org/data/works/corpus/): explicitly use `corpus=core`.
- [Open data license](https://help.openalex.org/data/how-its-built/): OpenAlex metadata is CC0.

These figures can change over time. `docs/rate-card.json` is an editable dated configuration accepted via `--rate-card`. Costs are estimates until reported by the API; a missing response cost remains unknown. The receipt distinguishes all request attempts, successful responses, and responses with reported costs. The estimate allows one extra exhaustion page; retry calls and live count drift are disclosed. No future allowance or price is guaranteed.

Institution selection uses `authorships.institutions.id`, not `lineage`. The exact filter and corpus parameter are saved in the receipt. ROR resolution must return the same ROR assertion; a different OpenAlex identity for an explicitly supplied OpenAlex ID is rejected. Resolution saves the full institution response. There is no name-based automatic selection.

The live API is not a frozen source and pages may change over a resumed run. The first observed version of each OpenAlex work ID is retained. Duplicate page records are recorded in the receipt and counted once. Frozen selected work assertions are stored in SQLite and hashed in ID order; the profile includes that hash separately from the corpus specification hash. Retained source assertions allow local reconstruction, while re-querying the live API can yield a different population. Changing retrieval dates does not alter the corpus hash; changing a material corpus default does.

Source fields are treated as data. HTML text is escaped and a restrictive content security policy is included. CSV formula-leading values are escaped. The transport sends credentials only in an Authorization header, refuses redirects, strips an exact credential echo from responses, and suppresses raw network exceptions. It does not use source text as instructions or call an LLM. Keep keys out of manual institution arguments and rate-card files as well.

## Live aggregate overview

The local interface uses [OpenAlex grouping](https://help.openalex.org/api/grouping/) with `:include_unknown`. Missing entity values can arrive as either `unknown` or a source-qualified ID ending in `/unknown`; both are normalized to the same unknown category. That category is excluded from the primary Field denominator. Primary Field, work type, and OA status groups are single-valued; institution/country groups are overlapping whole-work counts. Queries explicitly preserve the selected direct-institution and publication-date filters.

A maximum of 100 groups is requested per grouped query. Fields, types, OA statuses, and the permitted 50-year time range fit inside that bound. Sources and institutions are deliberately leading-group views, with limits declared in the export. Countries are similarly a leading view rather than an exhaustive country inventory. Publication drill-down uses an allowlist of filter fields and validated identifier values; the original corpus filters remain present. The standard API list limit of 10,000 records is exposed; the full CLI uses cursors for larger exports.

Boolean aggregation can conflate missing values with false, so it is not used to claim missing OA information. Positive OA/repository/retraction assertions are counted by explicit filters. Detailed resolved-authorship coverage remains unavailable in this overview and is not inferred from group counts. Funding coverage distinguishes funder links on works, award links on works, and Award records that explicitly name the selected recipient institution; none is treated as proof of complete funding attribution. No narrative generator is called.


## Coverage report revision

The browser report now uses `pharos-coverage-overview-v1` (implementation version 3). Open-access and repository-copy measures are not requested or included. The existing CLI contract is unchanged.

Publisher grouping uses `primary_location.source.host_organization`; only publisher IDs (`P…`) enter the publisher list. Institution hosts are not relabelled as publishers. Work-type filtering applies before both aggregation and publication drill-down. The primary source's direct publisher is used, not its parent lineage. This can reveal imprint distinctions and should not be read as an exhaustive parent-publisher distribution. Reported host coverage covers institution and publisher hosts together.

Raw-affiliation examples come from `sample=100,seed=42` with the exact saved corpus query. Per-string mappings in `authorships.affiliations` are authoritative: a flattened author-institution assignment alone is insufficient to assign every raw string on that authorship to the target. Each exact string counts at most once per sampled work. Counts and drill-down are limited to the sample; this is not a list of all institutional units. Results may change as the live index changes. See [raw affiliation strings](https://help.openalex.org/data/raw-affiliation-strings/) and [source host attributes](https://help.openalex.org/data/sources/attributes/).

## Experimental live inspection

Experimental panels are excluded from the saved aggregate report and its exports. The submitted-to-published candidate view requires both `locations.version:submittedVersion` and `locations.version:publishedVersion` on the same OpenAlex Work, then displays the matching location sources. It does not join separate Work records, prove that every submitted location is a preprint, or measure publication delay. OpenAlex uses `primary_location` for the copy closest to the version of record and may merge several hosted versions into one Work.

The author-profile inspection is deliberately not a researcher ranking. `authors.affiliations` identifies profiles whose affiliation history includes the institution, while `counts_by_year` counts every work on the author profile in that year. Those profile totals are shown only as context and are sorted alphabetically; they are not institution-specific output counts.
