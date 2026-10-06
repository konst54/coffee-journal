# Hosting and Supabase — not deployed yet

## Architecture decision v1
Canonical persistent SQLite serves Hermes ingestion immediately. Supabase initially stores an authenticated read-only projection `journal_snapshots` per owner. This choice avoids uploading source photographs/transcripts and postpones hosting credentials, but means cloud is NOT yet canonical. Read revision before publishing and require matching expected revision; do not overwrite newer remote data. Decide canonical store before allowing writes from more than one machine.

`web/main.js` contains only fictional fixtures. `createViewer(...).loadAuthenticated(adapter)` accepts `{dataset, authenticated:true}` only from a trusted authenticated adapter. Such an adapter is not implemented; the flag itself is not an authentication system.

## Setup remaining
1. Authorized Supabase project/account access is required; credentials were not found. Create project only with user authorization. Apply `supabase/migrations/001_projection.sql` once as owner.
2. Configure Auth without public signups if possible, create/invite intended owner, allowlist exact redirect URL. Insert authorized owner UUID into `journal_private.writers` via trusted administrator. Do not allow clients to edit this table.
3. Build backend publisher using normal owner's auth token (not broad service key); validated export excludes source fields. Read revision and call `publish_journal(p_dataset,p_expected_revision)`; GET exact owner projection afterwards and compare content/revision. Exponential retry only on network; 40001 requires explicit reconciliation, not blind overwrite.
4. Build frontend auth and reader: anonymous gets only demo; authenticated GET `/rest/v1/journal_snapshots?select=dataset,revision` with user JWT plus project publishable key. Verify session via `/auth/v1/user`. Keep tokens memory-only, clear on logout/expiry, never show live data based on a user-selected mode flag.
5. Verify two-user isolation and anon denial through hosted HTTP; verify token expiry/logout, denied writer, source exclusion, race/conflict. Do not equate local SQL test to cloud readiness.
6. Deploy only code/static demo to GitHub Pages; fetch live data after authentication. Private repo Pages availability depends on GitHub plan; do not change repo visibility to get free Pages without permission. Existing Hermes container cannot expose another public port; local 8765 is for tests only.

No hosted project, public URL, live sync, or remote CI was verified in this checkpoint.
