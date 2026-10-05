# Coffee Journal — agent contract

Read docs/HANDOFF.md first. User language: Russian. Read-only, compact mobile UI; ingestion through Hermes chat (voice/text/photos), not UI forms. Do not invent readings from photos or ambiguous slash notation. Unknown values are null. Originals and real records are private and NEVER committed. Never put service credentials in browser bundles.

## Shared contract v1
- Frontend: dependency-light ES modules in web/, static hosting compatible with GitHub Pages. Backend: Python stdlib in coffee_journal/, CLI `python3 -m coffee_journal`.
- JSON export: `{ "schema_version": 1, "coffees": [], "batches": [], "equipment": [], "recipes": [], "brews": [] }`.
- Each record: UUID string `id`; coffee: name, roaster, origin, process, variety, roast_level, labeled_notes (string), notes (string). Batch: coffee_id, roast_date (YYYY-MM-DD or null), initial_weight_g, notes. Equipment: name, kind ('brewer'|'grinder'), notes. Recipe: name, brewer_id, steps (array of {name,instruction,duration_s,water_g}), notes.
- Brew: batch_id (required), brewer_id, grinder_id, recipe_id, brewed_at (ISO8601 with timezone or null), temperature_c, grind_setting (string), coffee_g, water_g, duration_s, rating (integer 1–100 or null), taste_notes (string), recipe_notes (string), optional bypass_water_g, output_g, tds, extraction_yield, sensory (object), source_text (private). Ratios derived as water_g/coffee_g, never conflicting independent values.
- View joins brew→batch→coffee. No credentials/data in static export. No innerHTML for user content. Viewer demo data explicitly labeled fictitious.
- Local private SQLite path via COFFEE_JOURNAL_DB, default /opt/data/coffee-journal-private/journal.sqlite3. Source assets outside repo. Browser live data via Supabase authenticated SELECT + owner RLS, not public JSON.
- Never change another Hermes profile. Parent owns integrations, Git, docs and remote writes; child agents must not commit or push.

## SDLC
Small vertical features: acceptance → failing test → implementation → full tests → security review → commit + handoff. Each patch records limitations honestly. Required gate: `python3 -m unittest discover -s tests -v`; frontend `npm test` in web when available. Parent verifies browser at 390px and desktop. Main starts with bootstrap docs; unfinished code remains on feature branch, reviewed through PR. No automated production deployment or public personal data.
