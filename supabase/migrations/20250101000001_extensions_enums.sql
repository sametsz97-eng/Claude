-- 0001: Eklentiler, şemalar ve enum tipleri
-- ---------------------------------------------------------------

create extension if not exists pgcrypto with schema extensions;

-- "private" şeması: istemciye (anon/authenticated) tamamen kapalı.
-- Telefon/cihaz hash'leri, banlar, şikâyet defteri burada tutulur.
-- PostgREST bu şemayı yayınlamaz (config.toml -> api.schemas).
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

-- Postgres varsayılan olarak yeni fonksiyonlara PUBLIC execute verir; kapat.
alter default privileges in schema private revoke execute on functions from public;

create type public.gender_t as enum ('female', 'male');
create type public.report_category_t as enum ('harassment', 'profanity', 'nsfw', 'gender_mismatch');
create type public.match_status_t as enum ('active', 'ended');
