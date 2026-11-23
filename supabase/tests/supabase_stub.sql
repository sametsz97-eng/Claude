-- Sadece yerel test için: Supabase'in sağladığı nesnelerin minimal taklidi.
-- Gerçek Supabase projesinde ÇALIŞTIRMAYIN.
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
create schema auth;
create schema extensions;
grant usage on schema auth, extensions, public to anon, authenticated, service_role;
create table auth.users (id uuid primary key default gen_random_uuid(), phone text);
create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant execute on function auth.uid() to anon, authenticated, service_role;
create publication supabase_realtime;
