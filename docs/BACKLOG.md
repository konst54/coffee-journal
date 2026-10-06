# Next work (ordered)

1. P0: establish actual Supabase access and hosting choice; no secret values in chat/Git. Implement authenticated viewer + publisher, hosted two-user/anon security gates, then deploy and verify exact URL. Keep local ingestion operational during migration.
2. P0: audit-aware correction and atomic coffee+batch+brew import (including partial retry recovery), backup restore test. Preserve stable CLI contract used by Hermes; update installed skill if commands change.
3. P1: richer coffee and batch model from supplied references: producer/farm/altitude/decaf/certifications, pack/open/roast dates, weight remaining, separate bag descriptors vs personal notes. Nullable fields; migration tests. Clarify actual shorthand field order before importing user's handwritten photo.
4. P1: refine compact comparison with user: labels/legend for slash order, same grinder+batch context, roast age, optional sensory profile; no entry forms.
5. P1: private source assets: durable storage + provenance, safe image extraction review, no public assets or inferred data. Current personal photos/examples have NOT been imported.
6. P1: GitHub Actions workflow scope, branch protection, CI template activation, additional contract/security tests. Do not claim local CI is remote.

Acceptance for usable first release: real entry sent here → stored/read back → authenticated mobile viewer shows that exact brew → can compare with same coffee → verified unauthorized denial → rollback/backup documented.
