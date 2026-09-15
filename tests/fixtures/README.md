# Fixture provenance

`synthetic.json` is a fabricated edge-case work. Its IDs and counts are test-only and not production facts. It includes a script-like Field label and instruction-like abstract token to test treatment of external text as inert data.

`oxford-1900.json` contains the institution response and all three selected works returned by the public OpenAlex API on 2026-09-07 at 16:15 UTC:

- Institution: University of Oxford, https://openalex.org/I40120149
- ROR: https://ror.org/052gg0110
- Filter: `authorships.institutions.id:https://openalex.org/I40120149,from_publication_date:1900-01-01,to_publication_date:1900-12-31`
- Corpus: `core`
- Selection: `pharos.backends.openalex_api.SELECT`
- API count: 3; retrieved unique IDs: 3; final cursor: null.
- Work-assertion SHA-256: `8a4e651e766bb02a0f6b84ecb3561cc2545716a1983662c8a64aee0d0160d6d7`
- Live run: 3 successful calls; $0.0002 reported for two list calls; free singleton lookup; estimate conservatively allowed one additional terminal call.
- License: CC0, per https://help.openalex.org/data/how-its-built/.

No API key was used. This tiny corpus validates retrieval and calculation, not the historical correctness of OpenAlex's assertions or completeness of Oxford's output. Live results may change; offline tests use these frozen assertions.

`oxford-modern-aggregates.json` preserves public query responses for the modern Oxford 2019–2025 live overview, retrieved on 2026-09-07. It is CC0 OpenAlex metadata, using the same direct institution identifier and core-corpus policy as the historical fixture. Each entry includes exact public query parameters and its retrieval timestamp. These are aggregate assertions, not a full 168,935-record download.

The frozen capture contains 168,935 eligible works and 166,615 works with known primary Fields. The other 2,320 arrive under `https://openalex.org/fields/unknown`; regression tests verify that this source-qualified unknown bucket is not counted as classified. Annual and work-type distributions reconcile to the eligible population; subject shares reconcile to the classified population. These values are frozen test expectations, never production defaults.

Live drill-down was also checked: 2022 returned 24,272 matching works, Medicine returned 42,415, and University College London co-occurrence returned 11,614. All matched the captured chart counts. The first page of 2022 results contained only works dated 2022. Institution search returned the Oxford identity for the name “University of Oxford.”


The modern fixture was extended for the recognition report revision with direct publisher groups, source-host coverage, and a seeded 100-work affiliation sample. The sample contains 98 works with an explicit target-institution raw-string mapping. OA queries are no longer part of this recognition fixture. Tests verify that only target-mapped strings are retained and repeated authorships do not inflate counts. The included raw affiliation text is public OpenAlex metadata, treated as data rather than instructions.
