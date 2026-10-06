// Public configuration only. The publishable (anon) key is designed to ship in browsers;
// data protection comes from Auth + RLS. NEVER put a secret (server-side) key here
// (tests/test_repo_hygiene.py fails the build if one appears in the repository).
// Empty values = demo-only mode.
export const SUPABASE_URL = '';
export const SUPABASE_PUBLISHABLE_KEY = '';
