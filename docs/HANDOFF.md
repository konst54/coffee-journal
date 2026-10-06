# Handoff — Coffee Journal

STATUS: READY_FOR_HANDOFF

Owner: Claude may begin now. Hermes has finished this checkpoint and relinquishes development of this branch. This is an initial working checkpoint, NOT a production release. Hermes will not automatically resume development when quota resets. Local ingestion via the stable CLI may continue without changing code.

Verified implementation/docs checkpoint: `f82a639500f8680f710de12cd2b0fc22a57c7280`. This readiness-only commit follows it; Claude should use latest remote tip. Draft PR: https://github.com/konst54/coffee-journal/pull/1 .

## Repository / resume point
- Private repo: https://github.com/konst54/coffee-journal
- Branch: `feat/initial-journal`; `main` contains bootstrap only. Do not start from main or merge unfinished work blindly.
- Code checkpoint: `c7607b9adf115d730c4dd11ae0fefd90b794c0f3` (private CLI, viewer, SQL). Additional browser test and documentation included in final handoff commits; use the **latest remote tip**, not only this earlier code checkpoint.
- Working checkout on Hermes host: `/opt/data/coffee-journal`. No child agents still own work; their interrupted artifacts were inspected and completed by the parent.

## User contract
Russian replies. Read-only compact mobile viewing, no record-entry forms. Choose a coffee → compact slash-parameter lines → compare past brews and select today's preparation. Ingestion from this Hermes Telegram chat by dictation/text/handwritten notes/coffee bag photos. Attributes unknown or uncertain remain null / require clarification, not guesses. Core: temperature, grinder+setting, coffee/water grams, derived ratio, integer rating 1–100, brewer, datetime, duration, recipe, tasting notes. Separate planned recipe vs actual execution and bag descriptors vs personal notes. Requirements will evolve; do not overbuild optional fields.

## Implemented
- Python stdlib `coffee_journal`: create/read for coffee, batch, equipment, recipe, brew; strict validation of fields/types/dates/finite numbers/UUID, relational references/equipment kind; SQLite atomic per-record transactions and stable idempotency IDs with conflict detection.
- Private backups and source-excluding export with exclusive file creation. No update/delete yet, no multi-entity transaction. Application reference checks are NOT database-level FKs. See SECURITY caveats.
- `web/`: dependency-free static ES modules, explicit fictional demo, coffee/device/rating/recent filters, compact parameter strings + comments, up to 3 comparison selections, recipe/details. Relative paths compatible with Pages; not published.
- `supabase/migrations/001_projection.sql`: private owner read projection, RLS, anon denial, no direct client writes, allowlisted publisher RPC, optimistic revisions, recursive private-source exclusion. Local PostgreSQL/PGlite security tests; not applied to hosted Supabase.
- SDLC, security review, hosting plan, portable Hermes ingestion guide, backlog. CI template is intentionally in docs, not active GitHub Actions.

## Hermes link — actual state
Default-profile skill `coffee-journal` installed at `/opt/data/skills/productivity/coffee-journal/SKILL.md`. It resolves existing entities, parses text/voice/photos conservatively, stages private JSON, calls CLI with stable platform/chat/message/index request IDs and gets the returned record before claiming success. No new webhook/Telegram listener or gateway configuration required. Skill is local to this host, not automatically installed on Claude's machine; portable instructions: `docs/HERMES.md`.

Private canonical DB: `/opt/data/coffee-journal-private/journal.sqlite3`; initialized. Last verified brew list is empty. No user examples/photos have been registered, and synthetic tests use isolated scratch databases. Original attachments remain in chat cache, not durable imported assets. When actual photo ingestion occurs, copy sources privately before cache cleanup. DB/export/photo records are never committed; do not attempt to infer records from reference app screenshots.

## Verification — actual run 2026-10-06 05:37 UTC
- `python3 -m unittest discover -s tests -v`: 5 tests PASS, including all-entity validation, ID replay/conflict, reference and equipment kind checks, source exclusion, backup permissions and symlink refusal. CLI tests do real add→get/list readback on isolated temporary DBs.
- `npm test --prefix web`: 4 tests PASS (joins/sort/zero+null, literal XSS-like text/no entry forms, comparison limit, demo banner stays unless authenticated adapter resolves).
- `npm test --prefix tools/sql-check`: PASS; real PostgreSQL/PGlite evaluates owner read, cross-owner isolation, anon/read/RPC denial, no direct delete, writer allowlist, stale revision rejection, private keys nested exclusion and schema-envelope rejection. auth.uid is a test stub, not real GoTrue/JWT.
- `npm audit --prefix tools/sql-check --audit-level=moderate`: 0 vulnerabilities in observed run.
- Real Chromium via Playwright: PASS at 390px mobile and 1280px desktop, no page overflow or JS errors; exercised coffee/device/rating filters, comparison, details, fictional banner, no forms. Screenshot inspected: `/opt/data/cache/scratch/coffee-journal-mobile.png` (local, not repo).
- `python3 -m coffee_journal init` against actual default DB: ok; brew list `[]`.
- `git diff --check`: PASS. Tests ran locally only; remote CI/staging not claimed.

## Exact commands for Claude
```sh
git fetch origin
git switch feat/initial-journal
git pull --ff-only
python3 -m unittest discover -s tests -v
npm test --prefix web
npm ci --ignore-scripts --prefix tools/sql-check
npm test --prefix tools/sql-check
npm audit --prefix tools/sql-check --audit-level=moderate
python3 -m http.server 8765 --bind 127.0.0.1 --directory web
# In another terminal, Chromium installed:
uv run --with playwright==1.58.0 python tests/browser_smoke.py
```
Override CHROMIUM_PATH and COFFEE_VIEW_URL on other hosts. Override COFFEE_JOURNAL_DB for test/dev data. Screenshots default to Hermes scratch path; set COFFEE_SCREENSHOT elsewhere.

## Blockers / first concrete next step
**No Supabase account/project credentials configured; no hosted website, authenticated UI adapter, cloud publisher or live sync.** The UI only shows fixtures. Obtain authorized project/hosting access, then implement publisher and auth reader described in DEPLOYMENT. Read SECURITY first; staging needs two real users and anonymous HTTP tests. Do not publish private export JSON to Pages as a shortcut.

GitHub OAuth observed without workflow scope (repo/read:org/gist only); remote Actions not set up. `docs/ci-template.yml` can be activated after authorization. Private repository Pages may require a paid plan; do not change visibility without permission. Hermes container has no new public port route; localhost server is not a deployment.

Backlog order: real auth/publisher+viewer and verified hosting → atomic import and audit-aware correction/backup restore → richer nullable coffee/batch attributes → refined compact comparison and private asset storage. See `docs/BACKLOG.md` acceptance for first usable release.

## Ownership / quota
At latest primary quota check after recovery, short window was 1% used and weekly 19% used; the prior window reset during interruption. That is historical, not current quota. Do not burn quota simply to reach zero. Publish a resumable checkpoint before exhaustion; emergency fallback authorized only for final commit/push/handoff, never substantive implementation. Ordinary interruptions do not revoke scope; recover from current artifacts without asking the user again unless an explicit new instruction requires it.

READY_FOR_HANDOFF means Claude may begin from latest remote tip and update ownership/status in its own branch. If Claude is already editing, Hermes must not resume this branch even after quota resets.
