# Handoff — initial implementation in progress

Repository: https://github.com/konst54/coffee-journal (private). Branch feat/initial-journal. Bootstrap main aa82f91. User: Russian; flexible requirements; read-only compact mobile diary, ingestion from Hermes dictation/text/handwriting/photos of coffee bags. Do not interpret unreadable example photo as confirmed data. Need 1–100 integer ratings, temperature, grinder-specific grind, dose/water/derived ratio, brewer, duration, recipe, tasting comments.

## State
- Bootstrap contract committed and remote verified.
- Two agents implementing independent backend coffee_journal/ and viewer web/, strict TDD. Parent owns integration, SDLC, SQL security tests, Git and handoff.
- GitHub CLI persistent executable /opt/data/bin/gh. Existing OAuth has repo/read:org/gist but NOT workflow scope. Workflow pushes may be blocked: keep CI template documented and do not claim remote CI ran if unavailable.
- No Supabase configuration discovered. Do not claim hosted database or live production deployed. Local private SQLite intended as working ingestion today, cloud sanitized authenticated read projection later.
- Latest observed quota at task start: primary 40% used; secondary 16% used. Recheck before expensive phases.

## Resume
Read AGENTS.md, git status and all implementation files; never overwrite dirty child work. Run `python3 -m unittest discover -s tests -v`, `cd web && npm test`; SQL gate `cd tools/sql-check && npm ci && npm test`. These commands are pending until modules exist. Final actual results and blockers will replace this note.

## Data boundaries
Actual private DB /opt/data/coffee-journal-private/journal.sqlite3, never in Git. Original images in chat cache should be copied into private durable assets only on actual ingest. Demo fixtures are fictional and clearly labeled. Never send service_role secrets to browser. No other Hermes profiles modified.
