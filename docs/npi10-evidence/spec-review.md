# Independent Spec review

Authority: ORIGINAL workspace approved NPI-10 card/spec/coverage/execution rules.
Baseline `53c0037`; implementation `6a9803c`; re-review `426729c`.

Two P2 findings, both resolved with genuine RED then GREEN evidence:

1. Truncation could leave a worksheet name ending in an apostrophe. Reproduced
   independently with XlsxWriter; fixed by post-truncation stripping, with full
   region label retained in context. [RED](red-sheet.txt).
2. All/manual cache reuse could export the first save's provenance on omitted
   intent. Ambiguous omission now returns INVALID_REQUEST400; explicit intent
   must match provenance observed by the backend. Both population orders covered.
   [RED](red-review.txt), [GREEN](green-export.txt).

Final re-review: both resolved; no remaining blocking Spec findings identified.
Headers, visible IDs, sorting, saved membership, numeric serialization and generation
checks align with R2. No independent economic calculator. Full suite and desktop
acceptance were not rerun by the reviewer; production capacity remains unverified.
