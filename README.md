# Pharos

**See how OpenAlex sees your research.**

A local, open-source Python CLI that creates a descriptive institution portrait from OpenAlex. This repository implements the immediate institutional prototype milestone: exact ROR/OpenAlex ID resolution, dated corpus definitions, resource estimates, resumable retrieval, deterministic profiles, and portable exports.

Requires Python 3.11+ on macOS or Linux. No runtime dependencies. Install with `python3 -m pip install .`, or run from the checkout using `PYTHONPATH=src python3 -m pharos.cli`.

## Run

Set `OPENALEX_API_KEY` in your local environment using your preferred secret-management mechanism. Do not supply the key in command arguments, source code, or chat. A free OpenAlex account does not require a payment card; see the dated [pricing references](docs/methodology.md).

```sh
pharos https://ror.org/052gg0110 --start-year 2019 --end-year 2025 --out output/oxford --estimate-only
pharos https://ror.org/052gg0110 --start-year 2019 --end-year 2025 --out output/oxford --resume
```

The first command resolves the ID, saves the specification and estimate, and stops before retrieving the corpus. The second resumes that specification. Large estimates stop at the configured bounds; review `resource-estimate.json` before explicitly increasing `--max-records` (default 100,000) or `--max-cost-usd` (default $0.10). Estimates do not represent your remaining account balance.

A small, explicit anonymous preview works without a key:

```sh
PYTHONPATH=src python3 -m pharos.cli https://ror.org/052gg0110 --start-year 1900 --end-year 1900 --anonymous --out output/oxford-1900
```

If the directory already exists from validation, add `--resume`. A completed checkpoint rebuilds outputs offline. Repeat the exact original institution argument and years when resuming. To refresh from the live API, choose a new output directory.

The scope is visible in console output and serialized: direct institution assignment, all work types, core OpenAlex corpus, retained and flagged retractions, whole counting, primary Topic rolled up to Field. Other scope choices and name searches are intentionally unavailable in this milestone.

## Outputs

- `profile.html`: standalone, escaped HTML portrait, with no remote assets or scripts.
- `profile.json`: structured metrics, denominators, coverage, warnings, and source hashes.
- `corpus.yaml`: exact versioned selection and defaults.
- `retrieval-receipt.yaml`: calls, bytes, reported API costs when available, timestamps, state, and count discrepancies.
- `resource-estimate.json`: preflight resource estimate and dated rates.
- `work-ids.csv`: included OpenAlex IDs and available DOI/PMID assertions.
- `warnings.csv`: coverage and methodology warnings.
- `checkpoint.sqlite3`: frozen selected source assertions, identity, query, cursor, and request audit; keep this for reproducibility.

The YAML files use JSON syntax, a valid YAML 1.2 subset. Private credentials are never persisted. Output files are written atomically; pages and their next cursor commit together in SQLite. A directory lock prevents concurrent writers. Existing unrelated output directories are rejected. Do not edit a live checkpoint or run against an untrusted checkpoint directory.

## Validation

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Tests cover canonical measures, unknown metadata, exact ID normalization, identity mismatch, direct scope, current-year handling, source-text injection, interrupted/resumed retrieval, duplicates, budget bounds, and credential redaction. The CC0 Oxford 1900 fixture was captured from a complete live API retrieval on 2026-09-07, and is tested through the application and exports. It is a small correctness fixture, not a claim that historical coverage is complete. See [fixture provenance](tests/fixtures/README.md).

JSON Schemas live in `schemas/`; the canonical observation contract is in `src/pharos/contracts/`. The profiling module consumes canonical observations rather than OpenAlex dictionaries. See [methodology](docs/methodology.md) and the [profile specification](specifications/pharos-profile-v1.md).

## Prototype limitations

Only exact institution IDs are supported. The prototype does not implement name searches, other entity selectors, file uploads, Parquet snapshots, warehouses, comparison systems, ORBIT, or an LLM narrative. Authentication is tested with a mock secret; the real integration run uses anonymous access. A live free-key integration run requires a key supplied locally by the user.

The transport is a small standard-library HTTPS adapter, avoiding a third-party client dependency in this prototype. Responses are capped at 32 MiB per page, requests time out, server/network errors get bounded retries, and HTTP 429 pauses for a later explicit resume. Metrics run in memory after retrieval; record count is bounded but this is not a hard RAM quota. Download size is unknown before full records arrive; the receipt records actual bytes. API authorships may be truncated at 100, which is disclosed alongside affiliation-dependent results.

MIT-licensed code; captured OpenAlex metadata is CC0.

## Local research portrait interface

Start the local interface directly from the checkout (no installation required):

```sh
python3 pharos_web.py
```

Then open `http://127.0.0.1:8765`. To use another port, run `python3 pharos_web.py --port 8766`. After installation, the equivalent command is `pharos-web`. It binds only to the loopback address. `--port` and `--data` can change the local port and cache directory.

### Container and hosted mode

The default command remains loopback-only. Public binding is a separate, explicit mode with exact Host and Origin allowlists. Pharos does not use `Forwarded` or `X-Forwarded-*` headers to decide whether a request is trusted.

Build and run the same image locally, substituting the browser-visible authority you will actually use:

```sh
docker build -t pharos .
docker run --rm -p 7860:7860 \
  -e PHAROS_ALLOWED_HOSTS=localhost:7860 \
  -e PHAROS_ALLOWED_ORIGINS=http://localhost:7860 \
  pharos
```

The image runs as an unprivileged user, listens on `0.0.0.0:7860`, stores transient application data under `/data/pharos`, and exposes `GET /healthz`. No credential is included in the image. An operator-controlled `OPENALEX_API_KEY` may still be supplied as a container secret or environment variable; browser endpoints do not accept keys.

For a later Hugging Face Docker Space, copy the repository into a Docker Space and configure `PHAROS_ALLOWED_HOSTS` to its exact public Host value (for example `owner-name.hf.space`) and `PHAROS_ALLOWED_ORIGINS` to its exact HTTPS origin. Hosted mode assigns an opaque, HTTP-only, SameSite session cookie; jobs, saved reports, selected views, exports, and their temporary files are isolated under that session. Idle sessions expire after one hour by default and their directory is deleted; `PHAROS_SESSION_TTL` can configure a longer operational policy. Loading jobs are not removed mid-run. A process restart ends every session and the interface makes no durability promise. A duplicated private Space can set `OPENALEX_API_KEY` as a Space secret, never in repository variables or the Dockerfile.

Hosted report generation uses a fixed-size worker queue rather than creating one thread per request. OpenAlex work is capped at two simultaneous operations by default, the report waiting queue holds at most 16 jobs, and each hosted session may initiate at most 60 live operations in a sliding minute. Overload returns an explicit `429` or `503` response. Configure these bounds with `PHAROS_SESSION_RATE`, `PHAROS_NETWORK_CONCURRENCY`, and `PHAROS_QUEUE_SIZE`; lowering them does not alter report calculations.

Each hosted session may start five reports and 20 exports by default. A report has a five-minute wall-time deadline checked before and after every bounded OpenAlex request. A single export is capped at 32 MiB and cumulative exports at 128 MiB per session. Configure these with `PHAROS_SESSION_REPORTS`, `PHAROS_SESSION_EXPORTS`, `PHAROS_REPORT_TIMEOUT`, `PHAROS_MAX_EXPORT_BYTES`, and `PHAROS_SESSION_EXPORT_BYTES`. Local mode does not apply these public-service budgets.

Each hosted report is additionally capped at 250 OpenAlex queries and USD 0.50 of cost reported by OpenAlex responses. `PHAROS_REPORT_QUERIES` and `PHAROS_REPORT_COST_USD` configure those ceilings. Cached responses are counted conservatively when their recorded cost metadata is reused. The deadline and budgets stop work between requests; they cannot interrupt a single in-flight HTTPS call, for which the transport's existing timeout remains the bound.

The server handles SIGTERM and SIGINT by stopping HTTP intake, closing its socket, and giving queued workers a bounded opportunity to finish. Upstream or edge-level IP abuse protection is still required. In-process session limits are not a substitute for platform-level traffic controls.

The repository CI runs the complete Python suite, JavaScript syntax checks, a Docker build, a non-root-user assertion, the container health check, and allowed/hostile Host smoke tests. This checkout's development host does not have Docker installed, so container runtime verification must complete in CI or on a Docker-equipped machine before release. See [SECURITY.md](SECURITY.md) for reporting and deployment expectations.

### Session-only OpenAlex authentication

On an HTTPS hosted instance, a user may optionally submit an OpenAlex API key for the current ephemeral Pharos session. The key is sent in a JSON request body over HTTPS, held only in the server-side in-memory session object, and used as a Bearer header for that session's subsequent OpenAlex requests. It is never returned to the browser, placed in the session cookie or a URL, written to a response-cache key, report, export, log, or filesystem artefact, or stored by Pharos in browser storage. The input is cleared from the page immediately after submission.

The **Forget key** action removes it from the session immediately. A running report reads the current session credential separately for every OpenAlex request, so its next request proceeds without the forgotten key; only an HTTPS request already in flight cannot be recalled. Session expiry and process restart also discard it. The shared server necessarily receives the plaintext key, so this mode is not equivalent to local execution. Local users should continue to supply `OPENALEX_API_KEY` through their own environment or secret manager. A private duplicated Hugging Face Space should configure it as a Space secret.

Hosted mode rejects requests that omit Fetch Metadata as well as cross-site requests, caps live sessions at 200 by default (`PHAROS_MAX_SESSIONS`), and applies a 15-second client socket timeout (`PHAROS_REQUEST_TIMEOUT`). Whether the hosting proxy imposes stronger connection limits must still be verified on the target platform.

The equivalent direct hosted command is:

```sh
pharos-web --mode hosted --host 0.0.0.0 --port 7860 \
  --allowed-host owner-name.hf.space \
  --allowed-origin https://owner-name.hf.space
```

Search for an institution, researcher, funder, journal/source, or publisher by name or supported identifier and confirm the matching OpenAlex record. Institution reports use a selected period; the other entity reports cover all years. Funder reports accept Crossref Funder IDs and OpenAlex Funder IDs and show available Award records; missing amounts, investigators, recipients, dates, and titles remain explicitly unknown. Publisher reports include works whose primary source belongs to the selected OpenAlex publisher lineage, including recorded imprints and subsidiaries. Neither view is a complete commercial or administrative portfolio. No LLM is involved.

The interface uses a separately labelled aggregate overview. It counts across the selected corpus without downloading every record, which makes a large institution usable without first configuring an API key. This is not a `pharos-profile-v1` complete record-level profile. Detailed missing-OA-assertion, authorship-resolution, and affiliation-observability measures are not claimed by the overview. Funding views distinguish funder links, award-linked works, and Awards that name the institution, while retaining OpenAlex's incompleteness caveat. Primary subject, DOI, abstract, and primary source coverage are displayed. A full download estimate points advanced users to the existing CLI.

Completed reports also offer **Guide my review**, a deterministic, purpose-led checklist. Checklist items navigate to existing report evidence, and users may download a separate JSON review record containing their own status and notes. Optional model-assisted draft wording can be enabled with `PHAROS_SLM_ENDPOINT` and `PHAROS_SLM_MODEL`; it is visibly labelled, editable, provenance-recorded, and cannot set a review status or suitability verdict. Model assistance never alters report measures or canonical report exports. See `docs/REVIEW_GUIDE.md`.

Institution and source charts display leading returned groups, not exhaustive inventories. Institution and country counts are whole counts, can overlap, and are not rankings of research performance. Subject percentages use classified publications only. Source-qualified `unknown` keys are normalized before computing that denominator. The types panel retains all returned raw work types.

Successful anonymous or operator-key API queries are cached by parameters and UTC date, so interrupted overview generation reuses completed queries. Queries made with a browser-supplied session key use a separate cache inside that session directory; they are never served to another session or to an anonymous user and are deleted with the session. Saved overviews remain available with their retrieval date; reopening does not silently refresh them. Restarting generation after an error resumes from that day's appropriate cache. Live publication lists can change independently of a saved overview. Delete neither raw CLI checkpoints nor user data to refresh an overview; use a new `--data` directory if a fresh local overview is wanted.

**Download overview** exports structured counts, exact scope, source-query hashes, and retrieval provenance. It does not export all included publication IDs. Use the CLI's complete retrieval for that. API keys, if configured in the server's environment, are never returned to the browser. The local service rejects foreign Host/Origin values and does not accept credentials or arbitrary API filters from browser requests.


### Coverage first

The first report asks how OpenAlex covers the institution and where apparent gaps might be. It does not assess the institution's research. Open-access reporting is removed from this interface and its coverage-overview export; the original full CLI profile retains its existing measures for future analytical reporting. Its plain-language briefing uses fixed templates and visible calculations rather than an LLM.

Sources and direct publishers can be viewed for any returned work type, including preprints. Drill-down retains that type selection. Publisher parents are not rolled up, and institutional repository hosts are excluded from the publisher list. Host coverage includes all recorded host organisations and must not be interpreted as publisher coverage.

The raw-affiliation panel uses a seeded 100-work sample within the selected corpus. It retains only exact raw strings whose per-string `institution_ids` mapping contains the target institution. Repeated authors on the same work do not inflate a string's count. Original spelling variants remain separate. Click a string to see its sampled works. The view is an exploratory coverage aid, not a complete inventory or ranking of core departments; unmatched works outside the institution corpus cannot be discovered from this sample. Sample coverage and missing per-string mappings are explicit.

### Human-readable exports

Choose **PDF report**, **Excel workbook (.xlsx)**, **CSV tables**, or **JSON with provenance** next to **Download**. Exporting uses the completed overview held by the local application; it does not rerun OpenAlex queries. If a specific work type is selected for sources/publishers, that view is included and labelled. Reopen a portrait after restarting the server before exporting it.

All formats include the same content-based export snapshot ID, institution, period, retrieval dates, and population definitions. This ID identifies the exported view, including the selected source work type; it is separate from the corpus hash. PDF displays leading entries where explicitly labelled, whereas CSV and Excel retain every returned table item. None claims to contain the full work corpus.

- PDF is a paginated coverage report with a labelled annual line chart, counts, coverage, sources, sample affiliation examples, and methodology. It is generated from structured data rather than capturing the browser viewport.
- Excel contains Report, Measures, Sample works, and Queries sheets. Counts are numbers, dates are typed and formatted, and shares are formulas based on the corresponding numerator/denominator. Zero denominators display Unknown. Filters and frozen headers support browsing the long tables.
- CSV is a UTF-8 file with a BOM for Excel, in a long-table layout. Shares are fractions (0.25 means 25%); count, denominator, population, period, snapshot ID, and notes accompany the rows. Provenance and method rows are explicitly labelled. Formula-leading source strings are escaped.
- JSON retains the full structured overview and any selected source view.

PDF requires ReportLab (`python3 -m pip install '.[exports]'`). The local Codex bundled PDF runtime is discovered automatically when ReportLab is absent from the running Python; `PHAROS_EXPORT_PYTHON` can select another Python with ReportLab. Excel uses the Artifact Tool Node runtime. Codex's bundled runtime is discovered automatically; other installations can configure `PHAROS_EXPORT_NODE` and `PHAROS_EXPORT_NODE_MODULES` to an installed Artifact Tool runtime. No package is downloaded during an export. CSV and JSON remain dependency-free.

The saved sidebar shows the latest stored overview per material corpus scope, collapsing duplicate ID spellings without deleting any saved files. Coverage context and definitions are now near the report header. Collaboration listings use recorded country metadata and avoid inferring institutional relationships.

The report includes live record-inspection actions for missing Fields, DOIs, abstracts, and primary sources. The displayed gap counts remain values from the dated saved aggregate snapshot; opening a list runs the same institution and period filters against the live OpenAlex index, labels the result as live, and can export the visible page as CSV. Scope and secondary methodology are collapsed.

### Browser endpoint data boundary

- `GET /`, `/index.html`, `/app.js`, and `/style.css` serve packaged static files. `GET /healthz` reports process health and contains no report or credential data.
- `GET /api/config` reads saved aggregate-report metadata from the configured data directory. `GET /api/job` reads process-memory job state and completed report data.
- `POST /api/export` transforms an already completed in-memory aggregate report; it does not rerun aggregate OpenAlex queries.
- `POST /api/overview` starts a report job. It reuses a compatible saved aggregate report when present; otherwise it performs live OpenAlex requests and then saves the deterministic result.
- `GET /api/search`, `/api/venues`, `/api/publications`, `/api/composition`, `/api/funding-details`, `/api/researchers`, `/api/researcher-profile`, and `/api/version-pairs` perform live OpenAlex requests, with reusable dated response caching where implemented.

The browser can optionally submit an OpenAlex API key only to the dedicated HTTPS hosted-session endpoint. The key is retained in server memory and is not accepted as a report parameter, written to a cache, or returned to the browser. Saved aggregate values and later live inspection results remain separately labelled; hosting configuration does not change report calculations or export preparation.

### Render preview

The repository includes a `render.yaml` Blueprint for a single-instance, deterministic public preview. It deliberately starts on Render's free plan and without an operator OpenAlex key or public model inference. See [`docs/RENDER_DEPLOYMENT.md`](docs/RENDER_DEPLOYMENT.md) for deployment, custom-domain, retention, and verification instructions.

The browser report opens directly on a single tabbed destination rather than hiding the report behind a separate summary. Its Overview combines the four coverage measures and exact denominators with the annual, work-type, and Field trends so users can first judge whether the institution looks recognisable. Missing-record actions live only in Gap patterns. The visual treatment uses an institutional blue-grey palette, flat rules instead of dashboard cards, mono tabular figures, and a reserved red treatment only for missing-data lines.

Experimental live lookups are visually separated and excluded from report exports. Researcher affiliation-history candidates are alphabetical rather than ranked because author-profile yearly work counts are not institution-specific. The submitted-to-published location view is a candidate inspection tool based on two versioned locations on the same OpenAlex Work; it does not claim that every submitted location is a preprint or match separate Work records.
