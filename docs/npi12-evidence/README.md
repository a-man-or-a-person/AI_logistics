# Reproduce the new NPI-12 acceptance

Run from the isolated candidate repository root, with Python3.12, Node22.23.3 and
installed Microsoft Edge. Install `requirements-lock.txt` into an isolated virtualenv.
Set `REQUIRE_FRONTEND_BROWSER=1`, `PYTHONUTF8=1`. Keep private inputs out of this replay.
The exact locally executed commands and outcomes are in `quality-gates.json`.

```text
python -m pytest -ra --junitxml=docs/npi12-evidence/pytest-results.xml --basetemp=.scratch/npi12-pytest-clean
python docs/npi12-evidence/replay.py selection
python docs/npi12-evidence/replay.py all
python docs/npi12-evidence/replay.py navigation
python docs/npi12-evidence/replay.py freshness
python docs/npi12-evidence/replay.py medoid
python docs/npi12-evidence/export_live.py
python docs/npi12-evidence/empty_guard.py
python docs/npi12-evidence/measure.py
python docs/npi12-evidence/capacity_live.py
```

The five replays use the existing committed drivers on source596d9fb. Their adaptations
are literal and specific to this acceptance, not a maintained generalized test framework.
Generated scripts/profiles/source CSV live under this worktree's `.scratch/`; output
JSON/screenshots are written into the scenario evidence folders. Ensure ports5078–5083
are unused first; do not stop an unrelated listener. Each runner terminates only its own
server/browser. Source-row and browser assertions are executed by the drivers.

Run `measure.py` **before** `capacity_live.py`: the latter consumes the former's final
90,000-row synthetic CSV/cache. API timings and sequential working-set/peak are one-shot
measurements; capacity_live independently downloads/reopens the same-size fixture.
`export_live.py` contains its own deterministic fixture; it reopens actual downloaded
bytes with the existing independent test ZIP/XML reader, not the production serializer.

`startup.py` is an **environment-specific diagnosis**, not a portable green test:
it expects the already-running older personal5055 server and navigation-generated
synthetic CSV. It preserves that server and starts/terminates only its own5082 process.
Its recorded old-checkout static hashes are historical observations. In another
environment, inspect actual checkout/port/HTML and launch documented run.py with the
generated navigation fixture on a free port; do not fabricate the old-server condition.

`empty_guard.py` uses actual Edge with the existing controller/HTTP-stub test seam,
explicitly separate from live Flask proofs. Exact weights/invalid requests/ties/legacy
compatibility similarly retain their API/algorithm seams in the matrix.

All78 exact criterion wordings/inputs/results/limits are preserved in
`criterion-evidence.json`; `acceptance-matrix.md` renders that record. Authority hashes
refer to original approved local planning documents, which are intentionally not copied
wholesale into Git. Browser profiles, private data, temporary environments and downloaded
XLSX binaries are not publication artifacts; selected screenshots and synthetic HTTP/ZIP
inspection records provide the reviewable evidence.

The tracked report records G-02 as pending at commit time. Final exact-HEAD CI and the
76PASS/2UNVERIFIED disposition appear in the PR/publication supplement. Human acceptance
and production readiness remain UNVERIFIED. No report claims an unpublished commit has CI.
