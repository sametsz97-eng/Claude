-- 0002: Tablolar
-- ---------------------------------------------------------------
-- NOT: Telefon numarası hiçbir tabloda açık metin olarak tutulmaz.
-- Sadece auth.users içinde (Supabase Auth) durur; ban ve şikâyet
-- eşleştirmesi için HMAC-SHA256 hash'i kullanılır.

-- ---------- private ----------

-- Sunucu tarafı ayarlar (hash pepper'ı vb.). README'deki adımla doldurulur.
create table private.app_config (
  key   text primary key,
  value text not null
);

-- Kullanıcı -> telefon hash'i
create table private.identities (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  phone_hash text not null,
  created_at timestamptz not null default now()
);
create index identities_phone_hash_idx on private.identities (phone_hash);

-- Kullanıcı -> cihaz hash'leri (bir kullanıcının birden çok cihazı olabilir)
create table private.devices (
  user_id     uuid not null references auth.users (id) on delete cascade,
  device_hash text not null,
  first_seen  timestamptz not null default now(),
  last_seen   timestamptz not null default now(),
  primary key (user_id, device_hash)
);
create index devices_device_hash_idx on private.devices (device_hash);

-- Banlar: user_id, telefon hash'i ve cihaz hash'ine bağlanır.
-- Hesap silinse bile hash'ler kaldığı için ban devam eder.
create table private.bans (
  id          bigint generated always as identity primary key,
  user_id     uuid,
  phone_hash  text,
  device_hash text,
  reason      text not null,
  starts_at   timestamptz not null default now(),
  expires_at  timestamptz,               -- null = kalıcı
  created_at  timestamptz not null default now(),
  check (user_id is not null or phone_hash is not null or device_hash is not null)
);
create index bans_user_idx   on private.bans (user_id);
create index bans_phone_idx  on private.bans (phone_hash);
create index bans_device_idx on private.bans (device_hash);

-- Şikâyet defteri. "Kişi" = telefon numarası; böylece
--  * aynı kişi birden çok hesapla şikâyet etse de 1 sayılır,
--  * şikâyet edilen hesabını silip yeniden açsa da sayaç sıfırlanmaz (ömür boyu).
create table private.reports (
  id                  bigint generated always as identity primary key,
  reporter_user_id    uuid,
  reported_user_id    uuid,
  reporter_phone_hash text not null,
  reported_phone_hash text not null,
  match_id            uuid,
  category            public.report_category_t not null,
  note                text check (note is null or char_length(note) <= 500),
  created_at          timestamptz not null default now(),
  unique (reporter_phone_hash, reported_phone_hash),
  check (reporter_phone_hash <> reported_phone_hash)
);
create index reports_reported_idx on private.reports (reported_phone_hash, category, created_at);

-- Doğrulama denemeleri. FOTOĞRAF SAKLANMAZ; sadece sonuç.
create table private.verification_attempts (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users (id) on delete cascade,
  provider   text not null,
  success    boolean not null,
  created_at timestamptz not null default now()
);
create index verification_attempts_user_idx on private.verification_attempts (user_id, created_at);

-- ---------- public ----------

create table public.profiles (
  id                   uuid primary key references auth.users (id) on delete cascade,
  nickname             text not null,
  emoji                text not null,
  nickname_rerolls     int  not null default 0,
  gender               public.gender_t,
  gender_verified      boolean not null default false,
  verified_at          timestamptz,
  needs_reverification boolean not null default false,
  current_match_id     uuid,          -- FK aşağıda (matches tablosundan sonra)
  last_partner_id      uuid,          -- art arda aynı kişiyle eşleşmeyi önler
  created_at           timestamptz not null default now(),
  last_seen_at         timestamptz not null default now()
);

create table public.consents (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references public.profiles (id) on delete cascade,
  kind        text not null check (kind in ('age_18', 'kvkk_explicit')),
  version     text not null,
  accepted_at timestamptz not null default now()
);
create index consents_user_idx on public.consents (user_id, kind, version);

create table public.match_queue (
  user_id        uuid primary key references public.profiles (id) on delete cascade,
  gender         public.gender_t not null,
  enqueued_at    timestamptz not null default now(),
  last_heartbeat timestamptz not null default now()
);
create index match_queue_gender_idx on public.match_queue (gender, enqueued_at);

create table public.matches (
  id         uuid primary key default gen_random_uuid(),
  user_a     uuid not null references public.profiles (id) on delete cascade,
  user_b     uuid not null references public.profiles (id) on delete cascade,
  status     public.match_status_t not null default 'active',
  started_at timestamptz not null default now(),
  ended_at   timestamptz,
  ended_by   uuid,
  check (user_a <> user_b)
);
create index matches_user_a_idx  on public.matches (user_a);
create index matches_user_b_idx  on public.matches (user_b);
create index matches_started_idx on public.matches (started_at);

alter table public.profiles
  add constraint profiles_current_match_fk
  foreign key (current_match_id) references public.matches (id) on delete set null;

create table public.messages (
  id         bigint generated always as identity primary key,
  match_id   uuid not null references public.matches (id) on delete cascade,
  sender_id  uuid not null references public.profiles (id) on delete cascade,
  body       text not null check (char_length(btrim(body)) between 1 and 1000),
  created_at timestamptz not null default now()
);
create index messages_match_idx  on public.messages (match_id, created_at);
create index messages_sender_idx on public.messages (sender_id, created_at);

create table public.blocks (
  blocker_id uuid not null references public.profiles (id) on delete cascade,
  blocked_id uuid not null references public.profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (blocker_id, blocked_id),
  check (blocker_id <> blocked_id)
);
create index blocks_blocked_idx on public.blocks (blocked_id);
