# NPI-09 — temporary medoid representative

## Decision checkpoint before display implementation

2026-10-11 (Europe/Moscow): user explicitly answered **«Подтверждаю временный medoid»**
to the repeated business review. Approved semantics: geographical reference, a real
assigned destination selected by the backend using unweighted projected distances;
no warehouse or transport-hub recommendation.

**НАВЕРНО / ВРЕМЕННО: представитель кластера = существующий medoid. До реализации
отображения повторно подтвердить, что географический ориентир соответствует задаче
менеджера; при появлении иной задачи пересмотреть. Не считать выбор окончательным.**
Any semantic replacement requires a new business decision. This checkpoint was recorded
before production display changes, independently of decomposition approval.

Baseline: `53c003797961c31c8160b0bfc1b69ea2cfa6c15b`, fetched protected main; branch
`feat/npi09-medoid` created at that exact SHA in `.worktrees/npi09`.
PR #15 merged; HEAD `49ba3ad75dbbfff322054e068c9cca583f1c1245` passed
[required verification](https://github.com/a-man-or-a-person/AI_logistics/actions/runs/38157762448/job/114524156012)
with all steps successful, including mandatory Node/Edge and zero-skip checks.

Authority: original workspace `.scratch/next-product-iteration/` approved NPI-09 card,
spec, coverage matrix, tracker, order and execution requirements. Existing approved
test seams: Product API, existing Node/Edge frontend, real Flask/synthetic Pulse.
No additional seam approval is needed. `/implement` is not installed; the explicit
task and approved TDD/execution requirements supply the implementation workflow.

Scope: existing medoid summary/API regression; shared presentation formatter,
map labels and inspector; focused tests and CURRENT documentation/evidence.
Algorithms, saved membership, frozen requests, source validation, navigation,
table columns and XLSX remain unchanged. No NPI-10 worktree or environment accessed.

Existing calculation: minimize sum of Euclidean distances in the local projection,
without trip weights. Ties choose first in existing input order; Product locations
are ordered by descending trips then ID. Identity is `medoid_point_id` and
`representative.point_id`; projected coordinates are `medoid.x/y`, geographic
coordinates/name come from the actual `LocationPoint`. Cluster `point_ids` is saved
membership. Unresolved points are excluded before clustering; negative assignments
have no summary. Singleton and coincident members use the same rule. Changes to data
or volumes can change membership/input order and therefore representative.
