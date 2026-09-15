# Pharos product review guide

Pharos is a local coverage-report application for inspecting how OpenAlex represents research organisations, individual researchers, funders, journals and other sources, and publishers. It is descriptive: the interface should clearly distinguish recorded OpenAlex evidence from absence, inference, ranking, or administrative truth.

## Review request

Please review the application as a product editor and interaction-design critic. Focus on:

1. Whether users can predict what each landing-page choice will report before selecting it.
2. Whether scope, denominators, saved snapshots, live lookups, samples, and incomplete upstream metadata are explained at the moment they matter.
3. Whether headings and supporting copy are concise, human, and internally consistent.
4. Whether tab order reflects the primary user task for each entity.
5. Whether warnings are proportionate rather than repetitive or alarming.
6. Whether terms such as Work, Source, Award, Field, publisher lineage, primary location, linked output, and core corpus need clearer definitions.
7. Whether the interface ever implies completeness, causality, investigator status, institutional ownership, research quality, or commercial market share without evidence.
8. Whether empty, loading, error, saved, and live states give users a clear next action.

Return findings grouped as:

- Critical misunderstandings
- Interaction and information-architecture issues
- Copy edits
- Terminology inconsistencies
- Accessibility concerns
- Suggested revised flows

For every finding, quote the current wording or identify the relevant element/function and propose replacement copy or behaviour.

## Important product semantics

- Institution reports use a chosen date range and direct OpenAlex affiliation links.
- Researcher reports cover all years attached to one algorithmically resolved OpenAlex Author profile and include identity-resolution evidence.
- Funder reports open on Awards. They show actual OpenAlex Award records plus work-level aggregates, while retaining upstream incompleteness caveats.
- Journal/source cover works whose primary location is the selected OpenAlex Source.
- Publisher reports cover works whose primary source belongs to the selected publisher lineage, including recorded imprints and subsidiaries.
- Aggregate reports do not download the entire underlying Work corpus.
- Completed report data and successful API responses are cached locally. Live drill-downs may change independently as OpenAlex changes.

## Files to inspect first

- `docs/INTERACTION_MAP.md`: user flows and state transitions.
- `output/review/pharos-text-review.json`: generated inventory of user-facing text with source context.
- `src/pharos/web/index.html`: document structure and static copy.
- `src/pharos/web/app.js`: interaction and dynamic copy.
- `src/pharos/web/style.css`: presentation and responsive behaviour.
- `src/pharos/overview.py`: report semantics and limitations.
- `src/pharos/server.py`: local API and caching behaviour.
- `src/pharos/report_exports.py`: PDF, Excel, CSV, and JSON export semantics.

## Running locally

Use Python 3.11 or newer:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pharos-web --port 8766 --data output/review-session
```

Then open `http://127.0.0.1:8766/`. Live report generation calls the public OpenAlex API. The bundle intentionally contains no API key and no response cache.

Run the offline tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Privacy and packaging

The review bundle excludes `.git`, local configuration, API-response caches, generated report snapshots, virtual environments, and credentials. Included fixtures and examples are public or synthetic research metadata.
