import { PGlite } from '@electric-sql/pglite';
import { readFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const db = new PGlite();
await db.exec(`CREATE ROLE anon; CREATE ROLE authenticated; CREATE SCHEMA auth;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
GRANT USAGE ON SCHEMA auth TO authenticated; GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;`);
try { await db.exec(await readFile('../../supabase/migrations/001_projection.sql','utf8')); }
catch (e) { if (e.code !== 'ENOENT') throw e; }
const owner='11111111-1111-4111-8111-111111111111';
const other='22222222-2222-4222-8222-222222222222';
const empty={schema_version:1,coffees:[],batches:[],equipment:[],recipes:[],brews:[]};
async function as(role,uid,fn) {
 await db.exec('BEGIN');
 try { await db.exec(`SET LOCAL ROLE ${role}; SELECT set_config('request.jwt.claim.sub','${uid}',true)`); await fn(); }
 finally { await db.exec('ROLLBACK'); }
}
// Tracer bullet: before implementation table/RPC missing -> assertion fails.
assert.equal((await db.query(`SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='journal_snapshots') AS ok`)).rows[0].ok,true,'projection table must exist');
await db.query('INSERT INTO journal_private.writers(user_id) VALUES ($1)',[owner]);
await db.query('INSERT INTO public.journal_snapshots(owner_id,dataset) VALUES ($1,$2)',[owner,empty]);
await as('anon','',async()=>{
 await assert.rejects(db.query('SELECT * FROM public.journal_snapshots'),e=>e.code==='42501');
});
await as('anon','',async()=>{
 await assert.rejects(db.query('SELECT public.publish_journal($1,1)',[empty]),e=>e.code==='42501');
});
await as('authenticated',owner,async()=>{
 assert.equal((await db.query('SELECT * FROM public.journal_snapshots')).rows.length,1);
 await assert.rejects(db.query('DELETE FROM public.journal_snapshots'),e=>e.code==='42501');
});
await as('authenticated',other,async()=>{
 assert.equal((await db.query('SELECT * FROM public.journal_snapshots')).rows.length,0);
 await assert.rejects(db.query('SELECT public.publish_journal($1,0)',[empty]),e=>e.code==='42501');
});
await as('authenticated',owner,async()=>{
 const r=await db.query('SELECT public.publish_journal($1,1) AS revision',[empty]);assert.equal(r.rows[0].revision,2);
});
await as('authenticated',owner,async()=>{
 await assert.rejects(db.query('SELECT public.publish_journal($1,0)',[empty]),e=>e.code==='40001');
});
await as('authenticated',owner,async()=>{
 const sensitive={...empty,coffees:[{id:owner,name:'Secret',source_text:'private transcript'}]};
 await assert.rejects(db.query('SELECT public.publish_journal($1,1)',[sensitive]),e=>e.code==='23514');
});
await as('authenticated',owner,async()=>{
 const sensitive={...empty,brews:[{id:owner,sensory:{source_refs:['private.jpg']}}]};
 await assert.rejects(db.query('SELECT public.publish_journal($1,1)',[sensitive]),e=>e.code==='23514');
});
await as('authenticated',owner,async()=>{
 await assert.rejects(db.query('SELECT public.publish_journal($1,1)',[{...empty,extra:[]}]),e=>e.code==='23514');
});
await as('authenticated',owner,async()=>{
 await assert.rejects(db.query('SELECT * FROM journal_private.writers'),e=>e.code==='42501');
});
await db.close();
console.log('PASS: PostgreSQL projection, anonymous denial, owner read, cross-owner isolation, writer allowlist, no direct writes, optimistic revision, recursive private-source exclusion and unknown schema keys.');
