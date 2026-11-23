-- 0004: Giriş / onboarding RPC'leri (istemci çağırır)
-- ---------------------------------------------------------------

-- Her uygulama açılışında ve SMS girişinden hemen sonra çağrılır.
--  * Telefon hash'ini kaydeder (numara auth.users dışına çıkmaz)
--  * Cihaz hash'ini kaydeder
--  * Profil yoksa rastgele takma ad + emoji ile oluşturur
--  * Ban durumunu döner
create or replace function public.bootstrap_session(p_device_id text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid   uuid := private.require_uid();
  v_phone text;
  v_nick  record;
begin
  select regexp_replace(coalesce(u.phone, ''), '\D', '', 'g')
    into v_phone
    from auth.users u where u.id = v_uid;

  if v_phone is null or char_length(v_phone) < 8 then
    raise exception 'phone_required';
  end if;

  insert into private.identities (user_id, phone_hash)
  values (v_uid, private.hash_value('phone:' || v_phone))
  on conflict (user_id) do update set phone_hash = excluded.phone_hash;

  if p_device_id is not null and char_length(p_device_id) between 4 and 256 then
    insert into private.devices (user_id, device_hash)
    values (v_uid, private.hash_value('device:' || p_device_id))
    on conflict (user_id, device_hash) do update set last_seen = now();
  end if;

  if not exists (select 1 from public.profiles where id = v_uid) then
    v_nick := private.random_nickname();
    insert into public.profiles (id, nickname, emoji)
    values (v_uid, v_nick.nickname, v_nick.emoji)
    on conflict (id) do nothing;
  end if;

  update public.profiles set last_seen_at = now() where id = v_uid;

  -- Ban'lıysa kuyruk/sohbetten de çıkar
  if private.is_banned(v_uid) then
    perform private.kick_user(v_uid);
  end if;

  return private.session_state(v_uid);
end;
$$;

create or replace function public.get_session_state()
returns jsonb
language plpgsql stable
security definer
set search_path = ''
as $$
begin
  return private.session_state(private.require_uid());
end;
$$;

-- 18 yaş onayı + KVKK açık rıza
create or replace function public.accept_consents(p_version text, p_age_confirmed boolean, p_kvkk_accepted boolean)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
begin
  if p_version is distinct from private.consent_version() then
    raise exception 'consent_version_mismatch';
  end if;
  if not coalesce(p_age_confirmed, false) or not coalesce(p_kvkk_accepted, false) then
    raise exception 'consents_required';
  end if;
  if not exists (select 1 from public.profiles where id = v_uid) then
    raise exception 'profile_missing';
  end if;

  if not private.has_consents(v_uid) then
    insert into public.consents (user_id, kind, version)
    values (v_uid, 'age_18', p_version), (v_uid, 'kvkk_explicit', p_version);
  end if;

  return private.session_state(v_uid);
end;
$$;

-- Takma adı bir kez yeniden üret
create or replace function public.reroll_nickname()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid  uuid := private.require_uid();
  v_nick record;
begin
  v_nick := private.random_nickname();
  update public.profiles
     set nickname = v_nick.nickname, emoji = v_nick.emoji, nickname_rerolls = nickname_rerolls + 1
   where id = v_uid and nickname_rerolls < 1;
  if not found then
    raise exception 'reroll_limit';
  end if;
  return private.session_state(v_uid);
end;
$$;

-- Cinsiyet seçimi. Doğrulanmış cinsiyet, yeniden doğrulama istenmedikçe değiştirilemez.
-- Seçim/değişiklik doğrulamayı sıfırlar.
create or replace function public.set_gender(p_gender public.gender_t)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
  v_p   public.profiles;
begin
  if p_gender is null then
    raise exception 'gender_required';
  end if;
  if private.is_banned(v_uid) then
    raise exception 'banned';
  end if;
  if not private.has_consents(v_uid) then
    raise exception 'consents_required';
  end if;

  select * into v_p from public.profiles where id = v_uid;
  if v_p.gender_verified and not v_p.needs_reverification then
    raise exception 'gender_locked';
  end if;

  -- kilit sırası: önce kuyruk
  delete from public.match_queue where user_id = v_uid;

  update public.profiles
     set gender = p_gender, gender_verified = false, verified_at = null
   where id = v_uid;

  return private.session_state(v_uid);
end;
$$;

-- KVKK: hesabı sil. Banlar ve şikâyet defteri hash olarak kalır
-- (kötüye kullanımın önlenmesi; aydınlatma metninde belirtilmelidir).
create or replace function public.delete_account()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
begin
  perform private.kick_user(v_uid);
  delete from auth.users where id = v_uid;
end;
$$;

-- ---------------------------------------------------------------
-- Sadece service_role (Edge Function) çağırır.
-- Doğrulama sağlayıcısının sonucunu yazar. Fotoğraf asla buraya gelmez.
-- p_detected_gender: sağlayıcının tespit ettiği cinsiyet; profildeki
-- beyanla uyuşmazsa doğrulama başarısız sayılır.
create or replace function public.admin_mark_verified(
  p_user uuid, p_provider text, p_success boolean, p_detected_gender public.gender_t
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_p      public.profiles;
  v_ok     boolean;
  v_recent int;
begin
  select count(*) into v_recent
    from private.verification_attempts
   where user_id = p_user and created_at > now() - interval '1 hour';
  if v_recent >= 5 then
    raise exception 'too_many_attempts';
  end if;

  select * into v_p from public.profiles where id = p_user for update;
  if v_p.id is null then
    raise exception 'profile_missing';
  end if;
  if v_p.gender is null then
    raise exception 'gender_required';
  end if;

  v_ok := coalesce(p_success, false) and p_detected_gender = v_p.gender;

  insert into private.verification_attempts (user_id, provider, success)
  values (p_user, p_provider, v_ok);

  if v_ok then
    update public.profiles
       set gender_verified = true, verified_at = now(), needs_reverification = false
     where id = p_user;
  end if;

  return v_ok;
end;
$$;

-- Manuel moderasyon (service_role). p_hours null => kalıcı
create or replace function public.admin_ban(p_user uuid, p_hours int, p_reason text default 'manual')
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform private.apply_ban(
    p_user,
    case when p_hours is null then null else make_interval(hours => p_hours) end,
    coalesce(p_reason, 'manual'));
end;
$$;
