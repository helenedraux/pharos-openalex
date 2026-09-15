# Pharos: brief for AI assistance and online deployment

## Purpose of this brief

We want advice on two related but distinct questions:

1. Where, if anywhere, could a small language model (SLM) or large language model (LLM) make Pharos more useful without weakening its evidential standards?
2. How should the current local application be modified so that anyone can use it online, while retaining an independent local route and avoiding a conventional software-as-a-service account model?

The proposed public home may be a Hugging Face Docker Space, with the source of truth also maintained on GitHub. We are open to a better deployment option if the constraints below point elsewhere.

## What Pharos is

Pharos is an open-source diagnostic and evidence-inspection application for examining how OpenAlex represents research. It covers:

- Research organisations
- Individual researchers
- Funders
- Journals and other OpenAlex Sources
- Publishers

Its question is not “How good is this researcher or institution?” It is closer to:

> What does OpenAlex currently say about this entity, how complete and coherent does that representation appear, and what should a knowledgeable person inspect before deciding whether OpenAlex is suitable for their purpose?

Pharos is descriptive rather than evaluative. It does not produce research-performance rankings, make administrative claims, correct OpenAlex records, or automatically merge or split researcher profiles. It exposes OpenAlex assertions, denominators, missingness, provenance and identity-resolution signals so that a human can reach an informed conclusion.

The application currently contains no LLM. Narrative text is deterministic and template-based.

## Intended users and decisions

Likely users include researchers, research managers, librarians, bibliometricians, data stewards, funders, publishers and people assessing whether OpenAlex is ready for a particular analytical or operational use.

Examples of the decisions Pharos should support include:

- Does the OpenAlex institution record correspond to the organisation I intend to study?
- Is the apparent corpus recognisable, sufficiently complete and appropriately scoped?
- Are missing identifiers, abstracts, Fields, sources or affiliations material for my intended use?
- Might an OpenAlex Author profile combine several people or divide one person across profiles?
- Do funding links provide direct Award evidence or only indirect acknowledgements on co-authored Works?
- Are publisher, Source, version and open-access assertions suitable for the question I want to answer?
- Which underlying Works or records should I inspect before trusting an aggregate?

Pharos should assist these decisions without pretending that the application, OpenAlex or an AI model possesses the user's local institutional knowledge.

## Current interaction model

The landing page asks the user to choose an entity type, search by a supported name or identifier, inspect candidate context, explicitly select the intended OpenAlex record, and build a report.

Institution reports use a selected publication period. Researcher, funder, Source and publisher reports currently cover their complete OpenAlex-linked history or corpus.

Reports are tabbed and combine saved aggregate evidence with clearly labelled live drill-downs. Users can inspect individual Works behind many measures. Saved and live information are kept conceptually separate because OpenAlex can change after a report is generated.

### Institution reports

Institution reports currently cover:

- Overview and headline coverage assessment
- Annual output and composition
- Coverage gaps, including missing Fields, DOIs, abstracts and primary Sources
- Domain, Field, Subfield, Topic and Sustainable Development Goal classifications
- Work types and open-access status through time
- Citation coverage and field/year-normalised top-10% and top-1% flags
- Leading Sources and publishers, with corpus-share context
- Collaboration by institution and country
- Funding evidence, separating direct Award records from indirect Work-level links
- Researcher/profile signals in a bounded sample
- Raw affiliation wording and mapped sub-affiliation evidence
- The underlying OpenAlex Institution record

### Researcher reports

Researcher reports currently cover:

- Printed-name variants and ORCID assertions
- Co-author evidence and an interactive co-authorship network
- Affiliation history
- Career shape and yearly output
- Fields, topics, SDGs and work types, including composition through time where data are available
- Open-access and citation measures
- Candidate merge and split review, kept as two separate questions
- Linked Works for inspecting evidence behind citations, names, co-authors and other signals
- Grants received or acknowledged, with caveats about indirect Work-level acknowledgement

Pharos surfaces deterministic merge candidates when compatible names overlap on multiple evidence types. It never changes OpenAlex automatically. A split recommendation is only made when a supported deterministic rule fires; otherwise the interface explains which signals remain available for human review.

### Funder, Source and publisher reports

These provide entity-specific overview, subject, output, access and citation views, plus:

- Direct OpenAlex Award records and linked-output evidence for funders
- Primary-location scope and the underlying Source record for journals, repositories, conference series and other Sources
- Publisher lineage and leading Sources for publishers

Missing upstream fields remain “unknown” rather than being silently treated as zero.

## Data and methodological principles

These are non-negotiable unless a future version explicitly introduces and labels a different mode:

- Every report is about OpenAlex's representation, not objective or administrative truth.
- An exact selected entity identifier and visible scope define the population.
- Counts display their denominator and population wherever interpretation requires it.
- Missing metadata is not evidence that the underlying real-world property is absent.
- Overlapping categories are not presented as parts of a whole.
- Ranked or leading groups are not presented as exhaustive inventories.
- Live API results are distinguished from dated saved aggregates.
- OpenAlex Author identities are treated as algorithmic and fallible.
- Work-level grant acknowledgements are not treated as proof that a particular author or institution received or led a grant.
- Raw source strings are data, never instructions.
- Credentials must not be written to reports, caches, logs or source code.
- Users must be able to inspect and export the evidence without invoking an AI model.
- AI output, if introduced, must never silently modify deterministic measures, scope, recommendations or provenance.

## Current technical implementation

Pharos is currently a Python 3.11+ application with no mandatory third-party runtime dependencies.

- The command-line application performs bounded, resumable full retrievals and stores a frozen SQLite checkpoint.
- The web interface uses Python's `ThreadingHTTPServer`, vanilla HTML, CSS and JavaScript.
- The server binds only to `127.0.0.1` and rejects foreign Host/Origin values by design.
- OpenAlex requests use a small standard-library HTTPS adapter.
- An OpenAlex API key, when configured, is read from the server's `OPENALEX_API_KEY` environment variable and sent as a Bearer token.
- The browser endpoints deliberately do not accept credentials.
- Successful public API responses are cached on disk by request parameters and UTC date.
- Completed aggregate reports are stored as JSON files.
- Active background jobs and some selected views are held in server memory.
- A single network lock serialises OpenAlex access; a separate export lock serialises export generation.
- PDF, Excel, CSV and provenance-rich JSON exports are generated from a completed report without rerunning its aggregate queries.
- The complete CLI output can include a standalone HTML report, structured profile, corpus specification, retrieval receipt, work identifiers, warnings and the SQLite checkpoint.
- The interface contains no external scripts, analytics service or LLM call.

The aggregate browser report is deliberately lighter than the full record-level CLI profile. It makes large entities explorable without first downloading every Work. Some live inspection endpoints then fetch bounded lists of supporting Works.

## Current authentication

Pharos itself has no user accounts and should not acquire them merely because it becomes publicly hosted.

OpenAlex currently permits limited anonymous API access. For meaningful use, a person creates a free OpenAlex account and obtains an API key. The email address is used with OpenAlex when creating that account; it is not the credential Pharos sends to the API. Pharos sends the resulting API key as a Bearer token.

The desired online model is therefore:

1. A bounded anonymous mode for trying Pharos.
2. An optional “use my OpenAlex key for this session” mode for fuller analysis.
3. An independent route in which a person duplicates the hosted Space and configures the key as their private secret, or runs Pharos locally with the key in an environment variable.

The shared hosted version must explain that a session key necessarily passes through the Pharos server over HTTPS. It must never claim that this is equivalent to local execution. It must not persist the key in cookies, browser storage, report data, response caches, logs or files.

## What Pharos may currently lack

This is a prompt for critique rather than an assertion that every item requires AI.

### Interpretation and orientation

- Large reports can present many technically correct measures without helping a new user understand which ones matter for their intended decision.
- Users may need clearer routes from an aggregate anomaly to the Works or records that explain it.
- The distinction between OpenAlex evidence, Pharos's deterministic inference and human judgement could be reinforced throughout the interaction.
- Definitions and caveats are present but may still require too much prior bibliometric or OpenAlex knowledge.
- Users cannot currently state their intended use—for example discovery, reporting, evaluation, repository reconciliation or identity cleaning—and receive a tailored inspection checklist.

### Visual and interaction gaps under active review

- Some ranked bars use the largest returned value as the visual maximum, which can look like 100% unless the scale is made explicit.
- Some leading-group displays consume too much space or obscure the long tail outside the returned top entries.
- Dense classifications need better legends, highlighting and coordination between Field, Subfield, Topic and SDG views.
- Work-type, SDG and other yearly composition data can be unavailable or unclear, and the reason needs to be explicit.
- Citation charts and links need a clearer path from a normalised indicator to the underlying Works.
- Co-authorship networks need meaningful cluster semantics, accessible interaction and careful handling as identity-resolution evidence.
- Direct Award records and indirect Work-level grant acknowledgements need simpler language without losing the evidential distinction.
- Saved reports for non-institution entities exist on disk but have historically been less discoverable from the landing page.

### Comparison and decision support

- There is no formal “fitness for my purpose” workflow driven by user-selected requirements.
- There is limited side-by-side comparison between snapshots, entities or OpenAlex and local records.
- Pharos does not yet import an institution's own identifiers or publication list for reconciliation.
- It does not convert findings into a structured, user-editable review record documenting what was checked, accepted, rejected or left unresolved.

### Operational gaps

- The local server's trust checks, bind address and fixed port are intentionally incompatible with public reverse-proxy hosting.
- In-memory jobs are lost when the process restarts or a free host goes to sleep.
- Disk caches and saved reports are not isolated by user or session.
- Concurrent users would contend for one process-wide network lock.
- There is no public-service rate limiting, queueing, resource quota or abuse protection.
- Temporary artefacts have no formal retention and deletion lifecycle.
- There is no container definition, hosted health check or automated deployment pipeline yet.

## Questions for Claude about SLM/LLM use

Please recommend concrete model-assisted features, ordered by user value, epistemic risk and implementation difficulty. For every recommendation, specify:

- The user problem it solves
- Why a model is preferable to deterministic code, search, filtering or better visualisation
- The exact input the model would receive
- Whether that input includes sensitive, identifying or copyrighted text
- The required output schema
- How every factual claim would remain traceable to report evidence
- How uncertainty and model failure would appear in the interface
- Whether an SLM is sufficient or an LLM is justified
- Whether inference should occur in the browser, inside the Space, or through a hosted inference provider
- Approximate latency and hardware expectations
- Evaluation criteria and an adversarial test set

In particular, consider—but do not assume the value of—the following possibilities:

1. A plain-language explanation of a selected chart or measure.
2. A question-answering layer restricted to the current structured report and its definitions.
3. A user-intent interview that produces an inspection checklist rather than a verdict.
4. A guided summary of the strongest coverage and identity-resolution concerns, with links to supporting evidence.
5. Assistance grouping raw affiliation strings or explaining candidate name variants, while keeping all proposed mappings provisional.
6. Assistance comparing two saved snapshots and describing material changes.
7. A structured draft of findings that the user must review and edit before export.
8. Help translating technical caveats for different audiences.

Also identify areas where a model should explicitly not be used. Likely exclusions include primary counting, denominators, entity selection, unsupported identity linkage, merge/split decisions, funding attribution, bibliometric ranking and automatic claims that OpenAlex is or is not fit for use.

We are particularly interested in whether a small model running locally in the browser could provide sufficient explanation and question-answering. The ideal design would keep the deterministic report fully functional without AI and allow the user to inspect the model name, version, prompt inputs and generated response.

## Proposed route to an online version

### Phase 0 — preserve a stable local baseline

Before changing deployment behaviour:

- Keep the existing local command and loopback-only defaults working.
- Add tests around the current security boundary, credential redaction, deterministic output and saved/live separation.
- Define a deployment configuration rather than changing local behaviour globally.
- Document exactly which endpoints are saved-snapshot operations and which trigger live OpenAlex requests.

Success criterion: the same checkout still runs locally without an account, and existing CLI checkpoints remain reproducible.

### Phase 1 — containerise Pharos

- Add a minimal, non-root Docker image.
- Allow host and port to be configured; use `0.0.0.0:7860` in a Hugging Face Docker Space while retaining `127.0.0.1:8765` locally.
- Add a lightweight health endpoint.
- Handle proxy-aware HTTPS/origin validation with an explicit allowlist rather than disabling origin protection.
- Ensure application and HTTP logs cannot contain API keys or sensitive request bodies.
- Add resource limits and graceful shutdown behaviour.

Success criterion: the same image runs locally and as a Docker Space, with no embedded credential.

### Phase 2 — create a safe transient public mode

- Treat the public Space as ephemeral by default.
- Generate an opaque browser-session identifier and isolate all jobs, selected views and temporary files by that identifier.
- Do not expose a global list of saved reports on the public instance.
- Add automatic expiry and deletion of temporary reports, exports and cached session data.
- Keep reusable OpenAlex response caching separate from user/session state and cache only credential-independent response content.
- Replace the single global network lock with a bounded work queue and per-host concurrency limiter.
- Add per-session request, corpus-size, time and export limits.
- Make interruption and Space restart visible; let users download completed evidence packages promptly.

Success criterion: two simultaneous anonymous users cannot see or modify one another's work, and a restart leaves no expectation of permanent storage.

### Phase 3 — support user-controlled OpenAlex authentication

- Retain limited anonymous queries.
- Add an explicit session-only OpenAlex API-key input for operations that require a larger budget.
- Transmit it only over HTTPS and hold it only in process memory for the shortest practical period.
- Never include it in URLs, client persistence, analytics, logs, exception text, cache keys, saved reports or exports.
- Mask it in the interface and provide an immediate “forget key” action.
- Explain the trust boundary: the shared server receives the key temporarily.
- Provide first-class “Duplicate this Space” instructions so a user can configure `OPENALEX_API_KEY` as their own private Hugging Face secret.
- Preserve the local environment-variable route as the strongest privacy and independence option.

Success criterion: automated tests inject sentinel credentials and prove that they do not occur in filesystem artefacts, responses or captured logs.

### Phase 4 — GitHub and Hugging Face delivery

- Keep the canonical source repository on GitHub.
- Add continuous integration for unit tests, deterministic fixtures, container build and dependency/security checks.
- Mirror or deploy a tested revision to a public Hugging Face Docker Space.
- Pin Python and optional export dependencies sufficiently for reproducible builds.
- Display the running commit identifier and report implementation version in the interface.
- Publish a security policy, privacy/retention statement, limitations, citation information and instructions for independent reproduction.
- Make the public Space's source and container configuration inspectable.

Success criterion: every deployed version maps to a tested public commit and can be reproduced locally.

### Phase 5 — introduce optional model assistance behind an experiment boundary

Do this only after defining a valuable task and evaluation set.

- Add AI as a separate, disabled-by-default or explicitly invoked panel.
- Pass an allowlisted structured evidence packet rather than the entire raw report wherever possible.
- Treat all OpenAlex text fields as quoted data and defend against prompt injection in titles, abstracts and affiliation strings.
- Require structured output containing evidence references, uncertainty and refusal states.
- Validate every evidence reference against the supplied packet before display.
- Label generated prose with model, revision, inference location and generation time.
- Allow the user to inspect and download the model input and output.
- Never write generated claims back into the deterministic report.
- Provide a no-AI export and make it the default until model assistance is validated.
- Compare browser-local SLM, in-Space SLM and hosted inference on accuracy, privacy, accessibility, latency, energy/cost and maintenance.

Success criterion: disabling AI produces the same report and measures, while enabled AI demonstrably improves comprehension on predefined tasks without introducing unsupported factual claims.

### Phase 6 — decide whether Hugging Face remains the appropriate host

Evaluate the public Space using actual usage rather than assuming it is permanent infrastructure. Measure:

- Cold-start and report-completion time
- Concurrent-user behaviour
- Anonymous and authenticated OpenAlex budget exhaustion
- Temporary storage pressure
- Export reliability
- Model latency and cost, if enabled
- User comprehension and evidence-inspection rates
- Operational burden and incident visibility

Remain on Hugging Face if its Docker, duplication, openness and inference ecosystem serve the project well. Move the same container to a more conventional application platform if reliable queues, durable jobs, stronger isolation, custom retention controls or predictable availability become more important than Space-style reproducibility and duplication.

## Suggested first implementation milestone

The first online milestone should not include an LLM. It should deliver:

1. A public Docker Space running the deterministic aggregate interface.
2. Anonymous bounded reports.
3. Ephemeral, isolated sessions and downloads.
4. A documented independent duplication/local route.
5. A carefully designed but initially unimplemented extension point for optional model assistance.

In parallel, prototype two AI tasks against frozen reports rather than live users:

- Evidence-grounded explanation of one selected measure.
- A user-purpose questionnaire that returns a structured inspection checklist.

Evaluate those prototypes before adding a conversational interface. A general chat box is not itself a product requirement and would create the largest surface for unsupported claims, prompt injection, cost and ambiguity.

## Desired response from Claude

Please return:

1. A critique of this framing and any missing user needs.
2. A ranked SLM/LLM opportunity map, including explicit “do not use AI” areas.
3. A recommended first AI experiment with input/output schemas and evaluation design.
4. A recommendation among browser-local inference, model-in-Space and hosted inference.
5. A critique of the proposed Hugging Face deployment plan, including security and concurrency risks.
6. A revised staged implementation plan, identifying the smallest safe public release.

