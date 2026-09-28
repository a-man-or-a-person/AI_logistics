# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- `CONTEXT.md` at the repo root, when it exists.
- `docs/adr/`, reading ADRs relevant to the area being changed.

If either location does not exist, proceed silently. Domain documentation is created lazily when terms or architectural decisions need to be recorded.

## File structure

This is a single-context repository:

```text
/
|-- CONTEXT.md
|-- docs/adr/
`-- backend/, frontend/, ml/, tests/
```

## Use the glossary's vocabulary

When an output names a domain concept, use the term defined in `CONTEXT.md`. Do not replace an established term with a new synonym. If a required concept is missing, record that as a possible domain-modeling gap.

## Flag ADR conflicts

If proposed work conflicts with an existing ADR, surface the conflict explicitly instead of silently overriding the decision.
