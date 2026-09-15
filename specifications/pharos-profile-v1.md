# pharos-profile-v1

Population: unique observed OpenAlex work IDs returned by the saved direct-institution, inclusive-publication-date, core-corpus query. Preserve distinct manifestations and related works; retain and flag retractions. Raw type values are preserved, including unfamiliar future categories. Null/empty types use the display category `unknown`.

Every measure includes a count, denominator, population label, and percentage. A zero denominator produces a null percentage. Percentages round to six decimals. Counts are deterministic integers; narrative text only formats stored population counts and carries the source field path.

Annual counts include zero-output years. First/last observed years require at least one work. Minimum and maximum annual counts use all selected complete calendar years, including zeros; the retrieval year is incomplete and excluded from those extrema.

Subject classification requires a primary Topic with a usable Field ID. Each classified work contributes exactly once. Subject percentages use classified works only. Classified, unclassified, and eligible counts remain separate. Rounded percentages reconcile to 100 within 0.0000005 times the number of categories.

OA count requires a literal true OpenAlex `is_oa` assertion. Null/missing assertions remain unknown. OA share uses all eligible works; known-OA-information coverage appears separately. OA-status distribution retains raw statuses and an unknown bucket. Repository copies require an explicit `any_repository_has_fulltext=true` assertion, with separate repository-information coverage. These assertions do not determine reuse rights.

Each institution or country contributes once per work, regardless of the number of authors. Institution co-occurrence excludes the target institution. Country co-occurrence includes the home country, explicitly labelled. Shares use all eligible works and need not sum to 100. Authorships with at least one resolved institution count as resolved; unresolved coverage uses the complementary observed authorship count. A work has observable affiliations when at least one authorship has a resolved institution or a raw affiliation assertion. Authorship truncation is conservatively flagged whenever 100 or more authorships are observed.

Sources refer to `primary_location.source`, with source type in the label, not alternative publication locations. Missing source coverage is exposed.

Funding coverage is the presence of funder or award links, not an assertion that unlinked works had no funding. DOI, abstract, authorship, primary-subject, OA, source, work-type, repository, retraction, and affiliation coverage use eligible works unless the population explicitly says observed authorships.

No comparative, causal, performance, impact, or suitability claims are produced.
