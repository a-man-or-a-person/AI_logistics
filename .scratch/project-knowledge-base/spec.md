# PROJECT KNOWLEDGE BASE SPEC

Status: ready-for-agent

## Goal

Create a small canonical knowledge base that lets a developer, coding agent, product collaborator, or future voice conversation understand ИИ Логистика without reading refactor tickets, chat history, or migration reports.

The package must explain the current Product, Pulse inputs, five Product modes, runtime architecture, research and compatibility boundaries, the NEXT cluster table, LATER Bear work, constraints, and unresolved decisions. It is documentation work only: it records accepted domain decisions and the repository as it exists; it does not redesign or refactor the system.

The completed package should support these user outcomes:

1. A new developer can identify the Product entry points, runtime flow, component ownership, and authoritative detailed references before changing code.
2. A coding agent can distinguish CURRENT behavior from NEXT, LATER, RESEARCH, and LEGACY without relying on prior conversation.
3. A product collaborator can understand the logistician's workflow, the meaning of Pulse data, and the differences among all five Product modes.
4. A product collaborator can discuss the new table without mistaking it for an implemented feature or expanding it to Bear modes.
5. A maintainer can locate the source of truth for domain language, current architecture, detailed contracts, and open decisions without encountering competing definitions.

## Authoritative sources

Use sources in this precedence order:

1. `CONTEXT.md` is authoritative for product vocabulary, business meaning, Pulse forecast semantics, the CURRENT/TARGET distinction, new-table requirements, and accepted NEXT/LATER scope.
2. Current production code and its tests are authoritative for what EXISTS. In particular:
   - the Product mode catalog and adapters own the five-mode set, capabilities, parameter normalization, mode-specific eligibility, warnings, and result semantics;
   - `ClusteringService` owns shared request orchestration, Pulse aggregation, coordinate resolution, projection, full-graph construction, caching, data quality, and response assembly;
   - the clustering API owns the `/api/clustering/*` HTTP boundary and request IDs;
   - the clustering frontend owns presentation state and user interaction while consuming backend-published machine capabilities;
   - the legacy application routes and research packages establish the compatibility and RESEARCH boundaries.
3. `docs/clustering_product_v1_contract.md` is the detailed canonical Product v1 behavior/API contract.
4. `docs/clustering_product_v1_workflow.md` is supporting detail for the implemented Product workflow and frontend behavior.
5. Data, methodology, freeze, and research documents are supporting or historical evidence only within the scope stated in the audit below. They cannot override `CONTEXT.md` or current Product code/tests.

No earlier report, ticket, test count, deleted implementation, or superseded assumption may override these sources.

## Existing documentation audit

| Document | Classification | Retained role | Required treatment |
|---|---|---|---|
| `CONTEXT.md` | CANONICAL | Domain vocabulary, accepted product direction, Pulse semantics, table requirements, and Bear status | Preserve content; make only the smallest edits needed to label NEXT/LATER and point to unresolved decisions clearly. |
| `README.md` | SUPPORTING | Setup, run/test commands, and concise Product entry point | Keep operational content; add a short knowledge-base pointer rather than duplicating the new brief or architecture narrative. |
| `docs/clustering_product_v1_contract.md` | CANONICAL | Detailed current Product modes, filters, parameters, response behavior, errors, and compatibility contract | Leave detailed contracts here; link to it from the brief and current-state architecture. |
| `docs/clustering_product_v1_workflow.md` | SUPPORTING | Detailed current request/UI workflow | Retain; add a scope pointer only if needed to prevent it competing with the new architecture overview. Its existing responsive UI describes the current workspace and must not be misread as a requirement for the NEXT table, which is desktop-only. |
| `docs/clustering_data_contract.md` | SUPPORTING | Pulse field semantics, aggregation, spatial constraints, and research-era clustering data rules | Retain as detailed data/reference material; add a brief scope pointer if its generic title could make it look like the whole current Product contract. |
| `docs/clustering_methodology.md` | SUPPORTING | Reproducible research method and experiment outputs | Retain as RESEARCH; do not promote its stop point or mode subset to current Product truth. |
| `docs/clustering_contract_v1_freeze_report.md` | SUPPORTING | Frozen research evidence for algorithm/data invariants and known coordinate-quality limits | Retain as dated evidence; exclude its run results and thresholds from the high-level narrative except through links where useful. |
| `docs/clustering_contract_v1_research_report.md` | HISTORICAL | Dated research implementation record | Retain with its existing frozen-reference warning; do not reuse branch history, test counts, or superseded pilot conclusions in canonical docs. |
| `docs/analytics_evaluation_contract.md` | HISTORICAL | Deferred/blocked future price-evaluation track | Retain with its existing status warning; describe only as non-Product research/history. |
| `docs/predictive_ml_contract.md` | HISTORICAL | Deferred forecasting investigation | Retain with its existing status warning; never use it to imply that the Product builds forecasts. |
| `.scratch/product-mode-refactor/` | HISTORICAL | Refactor planning and closure evidence | Leave unchanged and outside the knowledge-base navigation. |

No audited document is REDUNDANT enough to delete in this stage. The new documents synthesize and route; they do not replace detailed contracts or historical evidence.

## Proposed canonical documents

### `CONTEXT.md`

Ownership: domain language and accepted product decisions.

Keep it the single source of truth for the logistician, Pulse forecast semantics, Current Product, target direction, new-table requirements, five Product modes, Bear status, and the Product/RESEARCH/LEGACY distinction. Add explicit NEXT/LATER labels and a pointer to the open-question register only where the current wording is ambiguous. Do not copy architecture internals into it.

### `docs/architecture/current-state.md`

Ownership: what the repository implements now.

Required contents:

- a short system overview;
- one durable system/context Mermaid diagram;
- one Product request/data-flow Mermaid diagram;
- Product runtime flow from frontend through `/api/clustering/*`, `ClusteringService`, Pulse aggregation, coordinate resolution, full `SpatialGraph`, Product mode catalog/adapter, and response presentation;
- ownership of Product mode capabilities and semantics by `ProductModeCatalog` and adapters;
- shared orchestration ownership by `ClusteringService`;
- the full-graph-before-business-filtering and induced-subgraph eligibility boundary;
- backend ownership of machine capabilities and frontend ownership of presentation;
- Product, RESEARCH, and LEGACY/compatibility boundaries;
- links to detailed Product and data contracts.

It describes CURRENT only. It must not contain the NEXT table design or LATER Bear integration. A third diagram is omitted unless the two required diagrams cannot make the Product/RESEARCH/LEGACY boundary unambiguous.

### `docs/project/project-brief.md`

Ownership: human-facing orientation and status-aware project narrative.

Target approximately 3–6 readable pages. Required contents:

- what ИИ Логистика is and who uses it;
- the supported planning/tender-preparation workflow without claiming automatic tender creation;
- Current Product and its five functional clustering modes;
- Pulse as the source of historical, current, and forecast data, with an explicit statement that the system does not generate forecasts;
- what each mode analyzes, the concepts that affect it, and the result it returns;
- the purpose and accepted Product scope of the NEXT table;
- a high-level system and architecture explanation linked to the current-state document;
- clear RESEARCH and LEGACY boundaries;
- compact CURRENT, NEXT, LATER, RESEARCH, and LEGACY sections;
- durable constraints and links to canonical detail;
- a short open-questions summary linked to the register;
- discussion starters grounded in unresolved decisions, not invented roadmap items.

The brief is the navigation hub. It may summarize core concepts once, but definitions and detailed contracts remain owned by the documents named in the content ownership matrix.

### `docs/project/open-questions.md`

Ownership: real unresolved product or technical decisions.

Each entry contains only:

- the question;
- why it matters;
- the decision or work it blocks;
- its status category when useful (`NEXT` or `LATER`).

Seed questions only when supported by an explicit unknown in `CONTEXT.md` or by a concrete implementation gap between NEXT requirements and CURRENT code. At minimum, preserve the unresolved business meaning and user-facing terminology/action for Bear. Candidate NEXT questions such as the API shape for table data or Pulse-row pagination belong here only if repository inspection confirms that no accepted decision already exists. This file is not a backlog and contains no implementation tasks.

## Content ownership matrix

| Concept | Canonical owner | Allowed summaries/pointers | Must not independently redefine it |
|---|---|---|---|
| Domain vocabulary and actor meanings | `CONTEXT.md` | Project Brief | Architecture, README, detailed contracts |
| Pulse historical/current/forecast meaning | `CONTEXT.md` | Project Brief; Product contract for field-level behavior | Predictive/deferred documents |
| CURRENT/NEXT/LATER product status | `CONTEXT.md` | Project Brief | Current-state architecture and research reports |
| Current runtime architecture and ownership boundaries | Current-State Architecture | Project Brief; workflow as detailed supporting reference | `CONTEXT.md` and README |
| Five-mode Product API and mode parameters | Product v1 Contract plus current code/tests | Project Brief and Current-State Architecture at summary level | Open Questions and research methodology |
| Pulse field and aggregation semantics | Clustering Data Contract plus current code/tests, subordinate to `CONTEXT.md` | Product contract and Current-State Architecture through pointers | Project Brief beyond a short plain-language summary |
| New-table product purpose and accepted requirements | `CONTEXT.md` | Project Brief | Current-State Architecture and existing Product v1 contract |
| Unresolved decisions | Open Questions, with domain questions linked back to `CONTEXT.md` | Project Brief summary | README, architecture, and historical reports |
| Setup and execution commands | README and repository configuration | Project Brief link only if useful | Other canonical documents |
| Research methods and dated findings | Existing methodology/freeze/research documents | Current-State Architecture and Project Brief as boundary descriptions | `CONTEXT.md` and Product contract |
| LEGACY compatibility behavior | Product v1 Contract and current code/tests | Current-State Architecture and Project Brief | Research documents |

## CURRENT / NEXT / LATER model

Use these labels exactly and attach one to every statement that could be mistaken for implemented scope:

- **CURRENT** — behavior demonstrably implemented in current code and protected by tests. This includes all five Product modes, neutral comparison, Pulse selection, point-based map/inspector behavior, the Product API, and retained compatibility routes.
- **NEXT** — accepted target work defined in `CONTEXT.md` but not implemented. This is the desktop cluster table and its point/Pulse-row detail flow for Geography, Geo+Cost, and Geo+Volume.
- **LATER** — accepted deferral. This includes Bear redesign/business clarification and Bear inclusion in the new table. It does not mean deprecated or scheduled.
- **RESEARCH** — experiments, evaluation methods, reports, and ML packages that do not become Product merely by existing or being reproducible.
- **LEGACY** — retained compatibility surfaces and historical implementations that are not the canonical Product workflow.

Drift prevention rules:

1. Every CURRENT architecture claim must have a current code or test anchor in the implementation evidence notes.
2. Every product meaning or future-scope claim must trace to `CONTEXT.md`.
3. The Current-State Architecture uses CURRENT facts only.
4. The Project Brief labels NEXT and LATER at the section and claim level where ambiguity is possible.
5. Detailed values, API schemas, and formulas are linked to their canonical contracts instead of copied unless a short summary is required for comprehension.
6. `forecast` is always described as Pulse-supplied forecast data, never as system-generated ML output.
7. Bear Cost and Bear Volume are CURRENT functional modes; only changes to Bear and its table integration are LATER.

## Cross-linking strategy

- README gains one compact “Project knowledge” entry pointing first to the Project Brief, then to `CONTEXT.md` and Current-State Architecture.
- The Project Brief acts as the hub and links outward to `CONTEXT.md`, Current-State Architecture, Open Questions, the Product v1 Contract, and only the most relevant supporting research/data references.
- Current-State Architecture links to the Product v1 Contract for precise API/mode behavior and to the Data Contract for Pulse/aggregation detail.
- Open Questions links to the exact canonical context section that establishes each unresolved domain question; it does not restate settled requirements.
- `CONTEXT.md` links to Open Questions for the maintained register and to the Project Brief for orientation, without taking on navigation prose.
- Existing documents receive at most a one-paragraph status/pointer note where their scope could otherwise compete with a canonical owner.
- Use repository-relative Markdown links. Avoid bidirectional links when one direction is sufficient to navigate and establish authority.

## Documents to modify

- `CONTEXT.md`: minimal status-label and open-question pointer clarification only if required after line-by-line comparison with the new package.
- `README.md`: add a compact knowledge-base entry; do not duplicate the Project Brief.
- `docs/clustering_product_v1_workflow.md`: only if a short supporting/current-workflow status note is needed to distinguish current responsive UI from the desktop-only NEXT table.
- `docs/clustering_data_contract.md`: only if a short supporting/data-contract status note is needed to prevent its generic title and smaller research mode set from competing with the current Product contract.

Conditional edits must be skipped when the existing wording and inbound links already make scope unambiguous.

## Documents to create

- `docs/architecture/current-state.md`
- `docs/project/project-brief.md`
- `docs/project/open-questions.md`

No separate diagram files, generated site, glossary duplicate, index, or documentation framework are needed.

## Documents intentionally left unchanged

- `docs/clustering_product_v1_contract.md`: remains the detailed current Product contract.
- `docs/clustering_methodology.md`: remains a concise RESEARCH procedure.
- `docs/clustering_contract_v1_freeze_report.md`: remains dated supporting research evidence.
- `docs/clustering_contract_v1_research_report.md`: remains historical research implementation evidence.
- `docs/analytics_evaluation_contract.md`: remains a deferred/blocked historical contract.
- `docs/predictive_ml_contract.md`: remains a deferred historical forecasting investigation.
- `.scratch/product-mode-refactor/`: remains historical issue-tracker material.
- Production code and tests: documentation must conform to them; this stage does not change behavior.

## Non-goals

- Refactoring code or changing Product behavior.
- Implementing the new table, its API, formulas, point details, or Pulse-row pagination.
- Redesigning, removing, or deprecating Bear Cost or Bear Volume.
- Building a forecasting model or describing Pulse forecast data as system-generated.
- Designing schemas, frontend components, mobile/tablet behavior for the NEXT table, or speculative API contracts.
- Converting RESEARCH into Product or choosing a winning clustering mode.
- Recounting the eight refactor tickets, commit history, migration sequence, exact test counts, deleted implementations, or temporary Ponytail findings.
- Cataloguing every class, function, API field, parameter table, or report artifact.
- Deleting existing documents or broadly rewriting accurate detailed contracts.
- Creating a backlog disguised as open questions.

## Validation criteria

The documentation package is complete only when all checks pass:

1. Every CURRENT architecture statement has been checked against current code and, where behavior is externally observable, an existing high-level test.
2. Every domain, Product direction, NEXT, and LATER claim is supported by `CONTEXT.md`.
3. All five Product modes are named and accurately summarized:
   - Geography analyzes spatial structure;
   - Geo+Cost combines connected geography with weighted ₽/km;
   - Geo+Volume combines connected geography with shipment volume/trip count;
   - Bear Cost finds connected high-cost anomalies and qualifying singletons;
   - Bear Volume finds connected high-volume anomalies and qualifying singletons.
4. Bear Cost and Bear Volume are described as CURRENT and functional, never deprecated; their redesign and table integration are LATER.
5. The NEXT table is explicitly limited initially to Geography, Geo+Cost, and Geo+Volume.
6. Forecast references say that Pulse supplies forecast data and that the system does not build its own forecast.
7. RESEARCH artifacts are not presented as Product, and LEGACY compatibility is distinguishable from the canonical Product path.
8. The Current-State Architecture contains no NEXT or LATER behavior except a pointer saying roadmap content is elsewhere.
9. The Project Brief marks planned functionality as NEXT or LATER and stays within the 3–6 page readability target.
10. Open Questions contains only unresolved decisions with “why it matters” and “what it blocks”; answered questions and implementation tasks are absent.
11. Core concepts have one owner in the content ownership matrix; other documents summarize briefly and link instead of redefining them.
12. Mermaid diagrams render and add distinct information; there are no more than three, with two preferred.
13. All repository-relative links resolve, headings are scannable, and no newly added status pointer contradicts its target.
14. Existing high-seam Product tests remain green, especially catalog, Product API, frontend contract, geography/business modes, and Bear behavior; documentation work must not require test changes.
15. Repository text search finds no new statement that implies system-generated forecasting, Bear deprecation, implemented NEXT table behavior, or Product ownership of research workflows.

The primary validation seam is a single end-to-end knowledge-base review beginning at the Project Brief: a reviewer must be able to follow its links and verify every status-sensitive claim against one canonical owner. Existing Product integration/contract tests provide the behavioral evidence; no new documentation test framework is required.

## Implementation plan

1. Build a private claim-to-source checklist from `CONTEXT.md`, the Product catalog/adapters, `ClusteringService`, the clustering API/frontend, legacy routes, and the highest Product contract tests. Completion criterion: every planned CURRENT statement and every status-sensitive product statement has exactly one authoritative source.
2. Make only necessary `CONTEXT.md` wording changes to expose NEXT, LATER, and unresolved decisions. Completion criterion: accepted domain meaning is unchanged and no architecture implementation detail has moved into the domain document.
3. Write Current-State Architecture from verified code flow. Use two Mermaid diagrams unless a third ownership diagram adds non-duplicate information. Completion criterion: the document describes only implemented runtime behavior and makes all ownership/boundary seams explicit.
4. Write the Project Brief as the navigation hub, using short summaries and pointers to canonical detail. Completion criterion: a reader with no repository history can answer the primary objective questions and distinguish CURRENT, NEXT, LATER, RESEARCH, and LEGACY.
5. Write Open Questions from explicit unknowns and confirmed implementation gaps only. Completion criterion: every item states why it matters and what it blocks, and none is a settled requirement or task.
6. Add minimal cross-links and only necessary scope notes to existing documents. Completion criterion: each core concept has one owner and every supporting/historical document is hard to mistake for current Product truth.
7. Run the validation criteria as one final pass: source traceability, terminology/status searches, link checks, Mermaid inspection, and the existing high-seam Product tests. Completion criterion: all 15 criteria pass without changing production code or tests.

## Need for tickets?

**NO.** This is one bounded documentation package with one evidence-gathering pass, three new documents, minimal pointer edits, and one shared validation gate. Splitting it by Markdown file would create coordination and duplication without an independent delivery or rollback boundary. The implementation plan above is sufficient; create a follow-up ticket only if validation uncovers a real code/document conflict or an unresolved decision that requires product authority.
