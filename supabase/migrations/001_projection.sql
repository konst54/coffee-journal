-- v1: canonical local journal -> private authenticated read projection.
-- Run once as the database owner. No service-role key is used by the viewer.
BEGIN;
CREATE SCHEMA journal_private;
REVOKE ALL ON SCHEMA journal_private FROM PUBLIC, anon, authenticated;
CREATE TABLE journal_private.writers (user_id uuid PRIMARY KEY);
REVOKE ALL ON journal_private.writers FROM PUBLIC, anon, authenticated;

CREATE FUNCTION journal_private.valid_dataset(d jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
 SELECT jsonb_typeof(d) = 'object'
 AND d->'schema_version' = '1'::jsonb
 AND (d - ARRAY['schema_version','coffees','batches','equipment','recipes','brews']) = '{}'::jsonb
 AND jsonb_typeof(d->'coffees') = 'array'
 AND jsonb_typeof(d->'batches') = 'array'
 AND jsonb_typeof(d->'equipment') = 'array'
 AND jsonb_typeof(d->'recipes') = 'array'
 AND jsonb_typeof(d->'brews') = 'array'
 AND octet_length(d::text) <= 2097152
 AND NOT jsonb_path_exists(d, '$.**.source_text')
 AND NOT jsonb_path_exists(d, '$.**.source_refs')
$$;
REVOKE ALL ON FUNCTION journal_private.valid_dataset(jsonb) FROM PUBLIC;

CREATE TABLE public.journal_snapshots (
 owner_id uuid PRIMARY KEY,
 dataset jsonb NOT NULL CHECK (journal_private.valid_dataset(dataset) IS TRUE),
 revision bigint NOT NULL DEFAULT 1 CHECK (revision > 0),
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.journal_snapshots ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.journal_snapshots FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.journal_snapshots TO authenticated;
CREATE POLICY owner_read ON public.journal_snapshots FOR SELECT TO authenticated
 USING ((SELECT auth.uid()) = owner_id);

CREATE FUNCTION public.publish_journal(p_dataset jsonb, p_expected_revision bigint)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE caller uuid := auth.uid(); current_revision bigint; next_revision bigint;
BEGIN
 IF caller IS NULL OR NOT EXISTS (SELECT 1 FROM journal_private.writers WHERE user_id = caller) THEN
  RAISE EXCEPTION 'Writer not authorized' USING ERRCODE = '42501';
 END IF;
 IF journal_private.valid_dataset(p_dataset) IS NOT TRUE THEN
  RAISE EXCEPTION 'Invalid projection' USING ERRCODE = '23514';
 END IF;
 IF p_expected_revision IS NULL OR p_expected_revision < 0 THEN
  RAISE EXCEPTION 'Expected revision required' USING ERRCODE = '23514';
 END IF;
 -- Serialize first publish too, so absent-row races cannot silently overwrite.
 PERFORM pg_advisory_xact_lock(hashtextextended(caller::text, 0));
 SELECT revision INTO current_revision FROM public.journal_snapshots WHERE owner_id = caller FOR UPDATE;
 IF COALESCE(current_revision, 0) <> p_expected_revision THEN
  RAISE EXCEPTION 'Projection changed; fetch before retry' USING ERRCODE = '40001';
 END IF;
 next_revision := COALESCE(current_revision, 0) + 1;
 INSERT INTO public.journal_snapshots(owner_id,dataset,revision,updated_at)
 VALUES(caller,p_dataset,next_revision,now())
 ON CONFLICT(owner_id) DO UPDATE SET dataset=excluded.dataset, revision=excluded.revision, updated_at=excluded.updated_at;
 RETURN next_revision;
END;
$$;
REVOKE ALL ON FUNCTION public.publish_journal(jsonb,bigint) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.publish_journal(jsonb,bigint) TO authenticated;
COMMIT;
