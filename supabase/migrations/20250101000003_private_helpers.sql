-- 0003: Dahili yardımcı fonksiyonlar (private şeması, istemci çağıramaz)
-- ---------------------------------------------------------------
-- Tüm SECURITY DEFINER fonksiyonlarda search_path = '' kullanılır ve
-- her nesne şemasıyla birlikte yazılır (search_path saldırılarına karşı).

create or replace function private.consent_version()
returns text language sql immutable as $$ select 'kvkk-v1' $$;

create or replace function private.require_uid()
returns uuid
language plpgsql stable
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
begin
  if v_uid is null then
    raise exception 'not_authenticated' using errcode = '28000';
  end if;
  return v_uid;
end;
$$;

create or replace function private.hash_value(p_value text)
returns text
language plpgsql stable
security definer
set search_path = ''
as $$
declare
  v_pepper text;
begin
  select value into v_pepper from private.app_config where key = 'hash_pepper';
  if v_pepper is null or char_length(v_pepper) < 32 then
    raise exception 'hash_pepper_not_configured';
  end if;
  return encode(extensions.hmac(p_value, v_pepper, 'sha256'), 'hex');
end;
$$;

-- Kullanıcıya (user_id, telefon hash'i veya cihazlarından biri üzerinden)
-- uygulanan en ağır aktif ban. Kalıcı ban önce gelir.
create or replace function private.active_ban(p_uid uuid)
returns private.bans
language sql stable
security definer
set search_path = ''
as $$
  select b.*
  from private.bans b
  where (b.expires_at is null or b.expires_at > now())
    and b.starts_at <= now()
    and (
      b.user_id = p_uid
      or b.phone_hash in (select i.phone_hash from private.identities i where i.user_id = p_uid)
      or b.device_hash in (select d.device_hash from private.devices d where d.user_id = p_uid)
    )
  order by b.expires_at desc nulls first
  limit 1
$$;

create or replace function private.is_banned(p_uid uuid)
returns boolean
language sql stable
security definer
set search_path = ''
as $$
  select (private.active_ban(p_uid)).id is not null
$$;

create or replace function private.has_consents(p_uid uuid)
returns boolean
language sql stable
security definer
set search_path = ''
as $$
  select
    exists (select 1 from public.consents c
            where c.user_id = p_uid and c.kind = 'age_18' and c.version = private.consent_version())
    and
    exists (select 1 from public.consents c
            where c.user_id = p_uid and c.kind = 'kvkk_explicit' and c.version = private.consent_version())
$$;

-- Rastgele Türkçe takma ad + emoji
create or replace function private.random_nickname(out nickname text, out emoji text)
language plpgsql volatile
set search_path = ''
as $$
declare
  v_adj text[] := array[
    'Sessiz','Neşeli','Gizemli','Uykucu','Meraklı','Cesur','Sakin','Hızlı','Utangaç','Bilge',
    'Şakacı','Hayalperest','Gezgin','Tatlı','Yıldızlı','Rüzgârlı','Kayıp','Parlak','Düşünceli','Yaramaz'];
  v_animals text[][] := array[
    ['Martı','🐦'],['Tilki','🦊'],['Baykuş','🦉'],['Kedi','🐱'],['Panda','🐼'],
    ['Yunus','🐬'],['Kirpi','🦔'],['Penguen','🐧'],['Kaplumbağa','🐢'],['Ahtapot','🐙'],
    ['Kelebek','🦋'],['Sincap','🐿️'],['Koala','🐨'],['Aslan','🦁'],['Tavşan','🐰'],
    ['Arı','🐝'],['Flamingo','🦩'],['Kurt','🐺'],['Ayı','🐻'],['Balina','🐳']];
  v_i int;
begin
  v_i := 1 + floor(random() * array_length(v_animals, 1))::int;
  nickname := v_adj[1 + floor(random() * array_length(v_adj, 1))::int] || ' ' || v_animals[v_i][1];
  emoji := v_animals[v_i][2];
end;
$$;

-- Aktif sohbeti bitirir (varsa). Profil satırlarındaki current_match_id temizlenir.
create or replace function private.end_match_internal(p_match_id uuid, p_by uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.matches
     set status = 'ended', ended_at = now(), ended_by = p_by
   where id = p_match_id and status = 'active';

  update public.profiles
     set current_match_id = null
   where current_match_id = p_match_id;
end;
$$;

-- Kullanıcıyı kuyruktan çıkarır ve aktif sohbetini bitirir.
-- Kilit sırası kuralı: önce match_queue, sonra matches/profiles.
create or replace function private.kick_user(p_uid uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_match uuid;
begin
  delete from public.match_queue where user_id = p_uid;
  select current_match_id into v_match from public.profiles where id = p_uid;
  if v_match is not null then
    perform private.end_match_internal(v_match, null);
  end if;
end;
$$;

-- Ban uygular: user_id + telefon hash'i + kullanıcının tüm cihaz hash'leri.
-- p_duration null ise kalıcı.
create or replace function private.apply_ban(p_uid uuid, p_duration interval, p_reason text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_phone   text;
  v_expires timestamptz := case when p_duration is null then null else now() + p_duration end;
begin
  select phone_hash into v_phone from private.identities where user_id = p_uid;

  insert into private.bans (user_id, phone_hash, device_hash, reason, expires_at)
  values (p_uid, v_phone, null, p_reason, v_expires);

  insert into private.bans (user_id, phone_hash, device_hash, reason, expires_at)
  select p_uid, null, d.device_hash, p_reason, v_expires
  from private.devices d where d.user_id = p_uid;

  perform private.kick_user(p_uid);
end;
$$;

-- Kullanıcının tekrar selfie doğrulaması yapmasını zorunlu kılar.
create or replace function private.require_reverification(p_uid uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform private.kick_user(p_uid);
  update public.profiles
     set needs_reverification = true,
         gender_verified = false
   where id = p_uid;
end;
$$;

-- İstemcinin gördüğü oturum durumu
create or replace function private.session_state(p_uid uuid)
returns jsonb
language plpgsql stable
security definer
set search_path = ''
as $$
declare
  v_ban private.bans;
  v_p   public.profiles;
begin
  v_ban := private.active_ban(p_uid);
  select * into v_p from public.profiles where id = p_uid;

  return jsonb_build_object(
    'banned',          v_ban.id is not null,
    'ban_until',       v_ban.expires_at,
    'ban_permanent',   v_ban.id is not null and v_ban.expires_at is null,
    'consent_version', private.consent_version(),
    'consents_ok',     private.has_consents(p_uid),
    'profile', case when v_p.id is null then null else jsonb_build_object(
        'nickname',             v_p.nickname,
        'emoji',                v_p.emoji,
        'can_reroll',           v_p.nickname_rerolls < 1,
        'gender',               v_p.gender,
        'gender_verified',      v_p.gender_verified,
        'needs_reverification', v_p.needs_reverification
      ) end,
    'current_match_id', v_p.current_match_id,
    'in_queue', exists (select 1 from public.match_queue q where q.user_id = p_uid)
  );
end;
$$;

-- Sohbete girebilir mi? Girmezse anlamlı hata kodu fırlatır.
create or replace function private.assert_can_chat(p_uid uuid)
returns public.profiles
language plpgsql stable
security definer
set search_path = ''
as $$
declare
  v_p public.profiles;
begin
  if private.is_banned(p_uid) then
    raise exception 'banned';
  end if;
  select * into v_p from public.profiles where id = p_uid;
  if v_p.id is null then
    raise exception 'profile_missing';
  end if;
  if not private.has_consents(p_uid) then
    raise exception 'consents_required';
  end if;
  if v_p.gender is null then
    raise exception 'gender_required';
  end if;
  if v_p.needs_reverification then
    raise exception 'reverification_required';
  end if;
  if not v_p.gender_verified then
    raise exception 'verification_required';
  end if;
  return v_p;
end;
$$;
