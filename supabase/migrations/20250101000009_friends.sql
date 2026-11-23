-- 0009: Arkadaşlık
-- ---------------------------------------------------------------
-- Kurallar:
--  * Sadece sohbet ettiğin (eşleştiğin) kişiye arkadaşlık isteği gönderebilirsin.
--  * Karşı taraf kabul edince arkadaş olursunuz. İki taraf birbirine istek
--    gönderirse otomatik kabul edilir.
--  * Günde en fazla 3 istek gönderebilirsin (Türkiye saatiyle gün başı sıfırlanır).
--    Silinen arkadaş veya reddedilen istek hakkı geri vermez.
--  * Arkadaşlıktan çıkarma her iki taraf için de arkadaşlığı ve mesaj geçmişini siler.
--  * Engelleme veya şikâyet, arkadaşlığı ve bekleyen istekleri de kaldırır.
--  * Arkadaş sohbetinde de şikâyet ve engelleme yapılabilir; şikâyet aynı ban
--    sayacına (ömür boyu, farklı kişi) işlenir.

create or replace function private.friend_daily_limit()
returns int language sql immutable as $$ select 3 $$;

create type public.friend_request_status_t as enum ('pending', 'accepted', 'declined');

create table public.friend_requests (
  id           uuid primary key default gen_random_uuid(),
  from_id      uuid not null references public.profiles (id) on delete cascade,
  to_id        uuid not null references public.profiles (id) on delete cascade,
  match_id     uuid references public.matches (id) on delete set null,
  status       public.friend_request_status_t not null default 'pending',
  created_at   timestamptz not null default now(),
  responded_at timestamptz,
  check (from_id <> to_id)
);
-- Bir çift arasında aynı anda tek bekleyen istek
create unique index friend_requests_pending_pair_idx
  on public.friend_requests (least(from_id, to_id), greatest(from_id, to_id))
  where status = 'pending';
create index friend_requests_from_idx on public.friend_requests (from_id, created_at);
create index friend_requests_to_idx   on public.friend_requests (to_id, status);

-- user_a < user_b. Silme yumuşak yapılır (removed_at); böylece Realtime,
-- RLS'e uyan bir UPDATE olayı ile karşı tarafa "arkadaşlık bitti" bildirir.
create table public.friendships (
  id              uuid primary key default gen_random_uuid(),
  user_a          uuid not null references public.profiles (id) on delete cascade,
  user_b          uuid not null references public.profiles (id) on delete cascade,
  origin_match_id uuid references public.matches (id) on delete set null,
  created_at      timestamptz not null default now(),
  removed_at      timestamptz,
  check (user_a < user_b),
  unique (user_a, user_b)
);
create index friendships_user_b_idx on public.friendships (user_b);

create table public.friend_messages (
  id            bigint generated always as identity primary key,
  friendship_id uuid not null references public.friendships (id) on delete cascade,
  sender_id     uuid not null references public.profiles (id) on delete cascade,
  body          text not null check (char_length(btrim(body)) between 1 and 1000),
  created_at    timestamptz not null default now()
);
create index friend_messages_friendship_idx on public.friend_messages (friendship_id, created_at);
create index friend_messages_sender_idx     on public.friend_messages (sender_id, created_at);

-- ---------- yardımcılar ----------

create or replace function private.friend_requests_sent_today(p_uid uuid)
returns int
language sql stable
security definer
set search_path = ''
as $$
  select count(*)::int
    from public.friend_requests r
   where r.from_id = p_uid
     and r.created_at >= (date_trunc('day', now() at time zone 'Europe/Istanbul')
                          at time zone 'Europe/Istanbul')
$$;

create or replace function private.is_blocked_pair(p_a uuid, p_b uuid)
returns boolean
language sql stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.blocks b
                  where (b.blocker_id = p_a and b.blocked_id = p_b)
                     or (b.blocker_id = p_b and b.blocked_id = p_a))
$$;

-- Arkadaşlığı kaldırır: mesaj geçmişini siler, satırı "removed" işaretler.
create or replace function private.remove_friendship_pair(p_a uuid, p_b uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_id uuid;
begin
  select id into v_id from public.friendships
   where user_a = least(p_a, p_b) and user_b = greatest(p_a, p_b) and removed_at is null
   for update;
  if v_id is not null then
    delete from public.friend_messages where friendship_id = v_id;
    update public.friendships set removed_at = now() where id = v_id;
  end if;
  update public.friend_requests
     set status = 'declined', responded_at = now()
   where status = 'pending'
     and least(from_id, to_id) = least(p_a, p_b)
     and greatest(from_id, to_id) = greatest(p_a, p_b);
end;
$$;

-- Engelle + arkadaşlığı/istekleri kaldır
create or replace function private.block_pair(p_blocker uuid, p_blocked uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.blocks (blocker_id, blocked_id)
  values (p_blocker, p_blocked)
  on conflict do nothing;
  perform private.remove_friendship_pair(p_blocker, p_blocked);
end;
$$;

-- Arkadaşlığı kur (veya daha önce silinmişse yeniden aç)
create or replace function private.create_friendship(p_a uuid, p_b uuid, p_match uuid)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_id uuid;
begin
  insert into public.friendships (user_a, user_b, origin_match_id)
  values (least(p_a, p_b), greatest(p_a, p_b), p_match)
  on conflict (user_a, user_b) do update
    set removed_at = null, created_at = now(),
        origin_match_id = coalesce(excluded.origin_match_id, public.friendships.origin_match_id)
  returning id into v_id;
  return v_id;
end;
$$;

-- ---------- şikâyet mantığını ortaklaştır ----------
-- Engelleme/sohbet bitirme çağıran tarafından yapılır; burası sadece defter + yaptırım.
create or replace function private.report_internal(
  p_uid uuid, p_partner uuid, p_match_id uuid,
  p_category public.report_category_t, p_note text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_reporter_hash text;
  v_reported_hash text;
  v_inserted      int;
  v_total         int;
  v_gm            int;
  v_verified_at   timestamptz;
begin
  if p_category is null then
    raise exception 'category_required';
  end if;

  select phone_hash into v_reporter_hash from private.identities where user_id = p_uid;
  select phone_hash into v_reported_hash from private.identities where user_id = p_partner;
  if v_reporter_hash is null or v_reported_hash is null then
    raise exception 'identity_missing';
  end if;
  if v_reporter_hash = v_reported_hash then
    return jsonb_build_object('counted', false);
  end if;

  perform pg_advisory_xact_lock(hashtextextended('report:' || v_reported_hash, 0));

  insert into private.reports (
    reporter_user_id, reported_user_id, reporter_phone_hash, reported_phone_hash,
    match_id, category, note)
  values (
    p_uid, p_partner, v_reporter_hash, v_reported_hash,
    p_match_id, p_category, nullif(left(btrim(coalesce(p_note, '')), 500), ''))
  on conflict (reporter_phone_hash, reported_phone_hash) do nothing;
  get diagnostics v_inserted = row_count;

  if v_inserted = 0 then
    return jsonb_build_object('counted', false);
  end if;

  select count(distinct reporter_phone_hash) into v_total
    from private.reports where reported_phone_hash = v_reported_hash;

  if v_total >= 9 then
    if not exists (select 1 from private.bans
                    where phone_hash = v_reported_hash and expires_at is null) then
      perform private.apply_ban(p_partner, null, 'reports_permanent');
    end if;
  elsif v_total = 6 then
    perform private.apply_ban(p_partner, interval '7 days', 'reports_level2');
  elsif v_total = 3 then
    perform private.apply_ban(p_partner, interval '24 hours', 'reports_level1');
  end if;

  if p_category = 'gender_mismatch' then
    select verified_at into v_verified_at from public.profiles where id = p_partner;
    select count(distinct reporter_phone_hash) into v_gm
      from private.reports
     where reported_phone_hash = v_reported_hash
       and category = 'gender_mismatch'
       and created_at > coalesce(v_verified_at, '-infinity'::timestamptz);
    if v_gm >= 3 then
      perform private.require_reverification(p_partner);
    end if;
  end if;

  return jsonb_build_object('counted', true);
end;
$$;

-- Rastgele sohbetteki kişiyi şikâyet et (önceki sürümün yerine geçer)
create or replace function public.report_partner(
  p_match_id uuid, p_category public.report_category_t, p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid     uuid := private.require_uid();
  v_m       public.matches;
  v_partner uuid;
begin
  if p_category is null then
    raise exception 'category_required';
  end if;
  select * into v_m from public.matches
   where id = p_match_id and v_uid in (user_a, user_b);
  if v_m.id is null then
    raise exception 'match_not_found';
  end if;
  v_partner := case when v_m.user_a = v_uid then v_m.user_b else v_m.user_a end;

  perform private.block_pair(v_uid, v_partner);
  perform private.end_match_internal(p_match_id, v_uid);
  return private.report_internal(v_uid, v_partner, p_match_id, p_category, p_note);
end;
$$;

-- Engelle (önceki sürümün yerine geçer): arkadaşlığı da kaldırır
create or replace function public.block_partner(p_match_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid     uuid := private.require_uid();
  v_m       public.matches;
  v_partner uuid;
begin
  select * into v_m from public.matches
   where id = p_match_id and v_uid in (user_a, user_b)
   for update;
  if v_m.id is null then
    raise exception 'match_not_found';
  end if;
  v_partner := case when v_m.user_a = v_uid then v_m.user_b else v_m.user_a end;

  perform private.block_pair(v_uid, v_partner);
  perform private.end_match_internal(p_match_id, v_uid);
end;
$$;

-- ---------- RPC'ler ----------

-- Sohbet ettiğin kişiye arkadaşlık isteği gönder
create or replace function public.send_friend_request(p_match_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid     uuid := private.require_uid();
  v_m       public.matches;
  v_partner uuid;
  v_reverse uuid;
  v_fid     uuid;
begin
  if private.is_banned(v_uid) then
    raise exception 'banned';
  end if;

  select * into v_m from public.matches
   where id = p_match_id and v_uid in (user_a, user_b);
  if v_m.id is null then
    raise exception 'match_not_found';
  end if;
  v_partner := case when v_m.user_a = v_uid then v_m.user_b else v_m.user_a end;

  -- Aynı çift için eşzamanlı istekleri seri hâle getir
  perform pg_advisory_xact_lock(
    hashtextextended('friend:' || least(v_uid, v_partner)::text || greatest(v_uid, v_partner)::text, 0));

  if private.is_blocked_pair(v_uid, v_partner) then
    raise exception 'friend_blocked';
  end if;
  if exists (select 1 from public.friendships
              where user_a = least(v_uid, v_partner) and user_b = greatest(v_uid, v_partner)
                and removed_at is null) then
    raise exception 'already_friends';
  end if;
  if exists (select 1 from public.friend_requests
              where from_id = v_uid and to_id = v_partner and status = 'pending') then
    raise exception 'friend_request_pending';
  end if;

  -- Kullanıcı başına günlük kotayı da seri hâle getir
  perform pg_advisory_xact_lock(hashtextextended('friend-quota:' || v_uid::text, 0));
  if private.friend_requests_sent_today(v_uid) >= private.friend_daily_limit() then
    raise exception 'friend_daily_limit';
  end if;

  select id into v_reverse from public.friend_requests
   where from_id = v_partner and to_id = v_uid and status = 'pending'
   for update;

  if v_reverse is not null then
    -- Karşı taraf zaten istek göndermiş: karşılıklı -> otomatik kabul.
    -- Kota için kendi isteğimizi de "accepted" olarak kaydediyoruz.
    update public.friend_requests set status = 'accepted', responded_at = now() where id = v_reverse;
    insert into public.friend_requests (from_id, to_id, match_id, status, responded_at)
    values (v_uid, v_partner, p_match_id, 'accepted', now());
    v_fid := private.create_friendship(v_uid, v_partner, p_match_id);
    return jsonb_build_object(
      'status', 'accepted', 'friendship_id', v_fid,
      'remaining_today', private.friend_daily_limit() - private.friend_requests_sent_today(v_uid));
  end if;

  insert into public.friend_requests (from_id, to_id, match_id)
  values (v_uid, v_partner, p_match_id);

  return jsonb_build_object(
    'status', 'sent',
    'remaining_today', private.friend_daily_limit() - private.friend_requests_sent_today(v_uid));
end;
$$;

-- Gelen isteği kabul et / reddet
create or replace function public.respond_friend_request(p_request_id uuid, p_accept boolean)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
  v_r   public.friend_requests;
  v_fid uuid;
begin
  select * into v_r from public.friend_requests
   where id = p_request_id and to_id = v_uid and status = 'pending'
   for update;
  if v_r.id is null then
    raise exception 'friend_request_not_found';
  end if;

  if not coalesce(p_accept, false) then
    update public.friend_requests set status = 'declined', responded_at = now() where id = v_r.id;
    return jsonb_build_object('status', 'declined');
  end if;

  if private.is_banned(v_uid) then
    raise exception 'banned';
  end if;
  if private.is_blocked_pair(v_uid, v_r.from_id) then
    update public.friend_requests set status = 'declined', responded_at = now() where id = v_r.id;
    raise exception 'friend_blocked';
  end if;

  update public.friend_requests set status = 'accepted', responded_at = now() where id = v_r.id;
  v_fid := private.create_friendship(v_uid, v_r.from_id, v_r.match_id);
  return jsonb_build_object('status', 'accepted', 'friendship_id', v_fid);
end;
$$;

-- Arkadaş listesi + gelen istekler + günlük kalan hak (tek çağrı)
create or replace function public.get_friends_overview()
returns jsonb
language plpgsql stable
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
begin
  return jsonb_build_object(
    'daily_limit',     private.friend_daily_limit(),
    'remaining_today', greatest(private.friend_daily_limit() - private.friend_requests_sent_today(v_uid), 0),
    'friends', coalesce((
      select jsonb_agg(jsonb_build_object(
               'friendship_id',   f.id,
               'nickname',        p.nickname,
               'emoji',           p.emoji,
               'since',           f.created_at,
               'last_message',    lm.body,
               'last_message_at', lm.created_at,
               'last_message_mine', lm.sender_id = v_uid
             ) order by coalesce(lm.created_at, f.created_at) desc)
        from public.friendships f
        join public.profiles p
          on p.id = case when f.user_a = v_uid then f.user_b else f.user_a end
        left join lateral (
          select m.body, m.created_at, m.sender_id from public.friend_messages m
           where m.friendship_id = f.id order by m.created_at desc limit 1) lm on true
       where v_uid in (f.user_a, f.user_b) and f.removed_at is null), '[]'::jsonb),
    'incoming', coalesce((
      select jsonb_agg(jsonb_build_object(
               'request_id', r.id,
               'nickname',   p.nickname,
               'emoji',      p.emoji,
               'created_at', r.created_at
             ) order by r.created_at desc)
        from public.friend_requests r
        join public.profiles p on p.id = r.from_id
       where r.to_id = v_uid and r.status = 'pending'), '[]'::jsonb),
    'outgoing_pending', (
      select count(*) from public.friend_requests r
       where r.from_id = v_uid and r.status = 'pending')
  );
end;
$$;

-- Arkadaş sohbeti başlığı: sadece takma ad + emoji
create or replace function public.get_friendship(p_friendship_id uuid)
returns jsonb
language plpgsql stable
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
  v_f   public.friendships;
  v_p   public.profiles;
begin
  select * into v_f from public.friendships
   where id = p_friendship_id and v_uid in (user_a, user_b);
  if v_f.id is null then
    raise exception 'friendship_not_found';
  end if;
  select * into v_p from public.profiles
   where id = case when v_f.user_a = v_uid then v_f.user_b else v_f.user_a end;
  return jsonb_build_object(
    'id',               v_f.id,
    'active',           v_f.removed_at is null,
    'since',            v_f.created_at,
    'partner_nickname', coalesce(v_p.nickname, 'Ayrılan kullanıcı'),
    'partner_emoji',    coalesce(v_p.emoji, '👤')
  );
end;
$$;

-- Arkadaşlıktan çıkar (silme)
create or replace function public.remove_friend(p_friendship_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
  v_f   public.friendships;
begin
  select * into v_f from public.friendships
   where id = p_friendship_id and v_uid in (user_a, user_b);
  if v_f.id is null then
    raise exception 'friendship_not_found';
  end if;
  perform private.remove_friendship_pair(v_f.user_a, v_f.user_b);
end;
$$;

create or replace function public.block_friend(p_friendship_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
  v_f   public.friendships;
begin
  select * into v_f from public.friendships
   where id = p_friendship_id and v_uid in (user_a, user_b);
  if v_f.id is null then
    raise exception 'friendship_not_found';
  end if;
  perform private.block_pair(v_uid, case when v_f.user_a = v_uid then v_f.user_b else v_f.user_a end);
end;
$$;

create or replace function public.report_friend(
  p_friendship_id uuid, p_category public.report_category_t, p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid     uuid := private.require_uid();
  v_f       public.friendships;
  v_partner uuid;
begin
  if p_category is null then
    raise exception 'category_required';
  end if;
  select * into v_f from public.friendships
   where id = p_friendship_id and v_uid in (user_a, user_b);
  if v_f.id is null then
    raise exception 'friendship_not_found';
  end if;
  v_partner := case when v_f.user_a = v_uid then v_f.user_b else v_f.user_a end;
  perform private.block_pair(v_uid, v_partner);
  return private.report_internal(v_uid, v_partner, v_f.origin_match_id, p_category, p_note);
end;
$$;

-- Arkadaş mesajları için hız sınırı + sunucu zamanı
create or replace function private.friend_messages_before_insert()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.created_at := now();
  new.body := btrim(new.body);
  if (select count(*) from public.friend_messages
       where sender_id = new.sender_id
         and created_at > now() - interval '10 seconds') >= 15 then
    raise exception 'rate_limited';
  end if;
  return new;
end;
$$;

create trigger friend_messages_before_insert
before insert on public.friend_messages
for each row execute function private.friend_messages_before_insert();

-- ---------- RLS ----------
alter table public.friend_requests enable row level security;
alter table public.friendships     enable row level security;
alter table public.friend_messages enable row level security;

revoke all on public.friend_requests, public.friendships, public.friend_messages
  from anon, authenticated;
grant select on public.friend_requests, public.friendships, public.friend_messages to authenticated;
grant insert (friendship_id, sender_id, body) on public.friend_messages to authenticated;

create policy friend_requests_select_own on public.friend_requests
  for select to authenticated
  using ((select auth.uid()) in (from_id, to_id));

create policy friendships_select_member on public.friendships
  for select to authenticated
  using ((select auth.uid()) in (user_a, user_b));

create policy friend_messages_select_member on public.friend_messages
  for select to authenticated
  using (exists (
    select 1 from public.friendships f
     where f.id = friend_messages.friendship_id
       and f.removed_at is null
       and (select auth.uid()) in (f.user_a, f.user_b)));

create policy friend_messages_insert_member on public.friend_messages
  for insert to authenticated
  with check (
    sender_id = (select auth.uid())
    and exists (
      select 1 from public.friendships f
       where f.id = friend_messages.friendship_id
         and f.removed_at is null
         and (select auth.uid()) in (f.user_a, f.user_b))
    and not private.is_banned((select auth.uid()))
  );

-- ---------- yetkiler ----------
revoke execute on all functions in schema private from public, anon, authenticated;
grant execute on function private.is_banned(uuid) to authenticated;

revoke execute on function
  public.send_friend_request(uuid),
  public.respond_friend_request(uuid, boolean),
  public.get_friends_overview(),
  public.get_friendship(uuid),
  public.remove_friend(uuid),
  public.block_friend(uuid),
  public.report_friend(uuid, public.report_category_t, text)
from public, anon;

grant execute on function
  public.send_friend_request(uuid),
  public.respond_friend_request(uuid, boolean),
  public.get_friends_overview(),
  public.get_friendship(uuid),
  public.remove_friend(uuid),
  public.block_friend(uuid),
  public.report_friend(uuid, public.report_category_t, text)
to authenticated;

-- ---------- realtime ----------
alter publication supabase_realtime
  add table public.friend_messages, public.friend_requests, public.friendships;
