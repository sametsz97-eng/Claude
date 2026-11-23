-- 0005: Eşleşme kuyruğu
-- ---------------------------------------------------------------
-- Model:
--  * Her kullanıcı en fazla bir aktif sohbette olabilir (profiles.current_match_id).
--  * Eşleşme her zaman 1 kız + 1 erkek arasında kurulur; böylece aktif
--    sohbetteki kız ve erkek sayısı daima eşittir. Fazla olan taraf kuyrukta bekler.
--  * İstemci kuyruktayken ~5 sn'de bir heartbeat_queue() çağırır. 30 sn'dir
--    heartbeat göndermeyen kayıt "aktif" sayılmaz, 2 dk sonra silinir.
--
-- Yarış durumları:
--  1. Çağıranın kuyruk satırı FOR UPDATE ile kilitlenir. Aynı kullanıcı için
--     paralel iki çağrı sıraya girer.
--  2. Aday FOR UPDATE SKIP LOCKED ile seçilir: başka bir transaction'ın
--     kilitlediği aday atlanır, böylece aynı kişi iki kez eşleşmez ve
--     beklemeden kaynaklı deadlock olmaz.
--  3. A ve B aynı anda birbirini atlarsa ikisi de beklemede kalır; bir
--     sonraki heartbeat'te (≈5 sn) eşleşirler.
--  4. Kilit sırası kuralı (tüm fonksiyonlarda): önce match_queue, sonra
--     matches/profiles. Profil kilidi tutarken kuyruk satırı kilitlenmez.

create or replace function private.queue_status(p_uid uuid)
returns jsonb
language plpgsql stable
security definer
set search_path = ''
as $$
declare
  v_q        public.match_queue;
  v_position int;
  v_opposite int;
  v_same     int;
  v_rate     numeric;  -- dakikadaki eşleşme sayısı
  v_eta      int;
begin
  select * into v_q from public.match_queue where user_id = p_uid;
  if v_q.user_id is null then
    return jsonb_build_object('status', 'idle');
  end if;

  select count(*) into v_position
    from public.match_queue q
   where q.gender = v_q.gender
     and q.last_heartbeat > now() - interval '30 seconds'
     and (q.enqueued_at, q.user_id) <= (v_q.enqueued_at, v_q.user_id);

  select count(*) into v_same
    from public.match_queue q
   where q.gender = v_q.gender and q.last_heartbeat > now() - interval '30 seconds';

  select count(*) into v_opposite
    from public.match_queue q
   where q.gender <> v_q.gender and q.last_heartbeat > now() - interval '30 seconds';

  select count(*)::numeric / 10 into v_rate
    from public.matches m
   where m.started_at > now() - interval '10 minutes';

  if v_opposite >= greatest(v_position, 1) then
    v_eta := 5;  -- karşı tarafta yeterli kişi var, bir sonraki turda eşleşme beklenir
  else
    -- önümdeki (karşı tarafta karşılığı olmayan) kişi sayısı / eşleşme hızı
    v_eta := ceil(greatest(v_position - v_opposite, 1) / greatest(v_rate, 0.1) * 60)::int;
  end if;

  return jsonb_build_object(
    'status',           'waiting',
    'position',         v_position,
    'same_waiting',     v_same,
    'opposite_waiting', v_opposite,
    'eta_seconds',      least(v_eta, 3600)
  );
end;
$$;

create or replace function private.try_match(p_uid uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_q     public.match_queue;
  v_p     public.profiles;
  v_cand  uuid;
  v_match uuid;
begin
  -- Bayat kayıtları temizle
  delete from public.match_queue where last_heartbeat < now() - interval '2 minutes';

  select * into v_q from public.match_queue where user_id = p_uid for update;

  select * into v_p from public.profiles where id = p_uid;
  if v_p.current_match_id is not null then
    delete from public.match_queue where user_id = p_uid;
    return jsonb_build_object('status', 'matched', 'match_id', v_p.current_match_id);
  end if;

  if v_q.user_id is null then
    return jsonb_build_object('status', 'idle');
  end if;

  update public.match_queue set last_heartbeat = now() where user_id = p_uid;

  select q.user_id into v_cand
    from public.match_queue q
    join public.profiles p on p.id = q.user_id
   where q.gender <> v_q.gender
     and q.user_id <> p_uid
     and q.last_heartbeat > now() - interval '30 seconds'
     and p.current_match_id is null
     and p.gender_verified
     and not p.needs_reverification
     -- engellenenlerle (iki yönde) asla eşleşme yok
     and not exists (
       select 1 from public.blocks b
        where (b.blocker_id = p_uid and b.blocked_id = q.user_id)
           or (b.blocker_id = q.user_id and b.blocked_id = p_uid))
     -- art arda aynı kişiyle eşleşme yok
     and v_p.last_partner_id is distinct from q.user_id
     and p.last_partner_id is distinct from p_uid
     and not private.is_banned(q.user_id)
   order by q.enqueued_at, q.user_id
   limit 1
   for update of q skip locked;

  if v_cand is null then
    return private.queue_status(p_uid);
  end if;

  insert into public.matches (user_a, user_b)
  values (p_uid, v_cand)
  returning id into v_match;

  delete from public.match_queue where user_id in (p_uid, v_cand);

  update public.profiles
     set current_match_id = v_match,
         last_partner_id  = case when id = p_uid then v_cand else p_uid end
   where id in (p_uid, v_cand);

  return jsonb_build_object('status', 'matched', 'match_id', v_match);
end;
$$;

-- Kuyruğa gir ve hemen eşleşme dene
create or replace function public.join_queue()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
  v_p   public.profiles;
begin
  v_p := private.assert_can_chat(v_uid);

  if v_p.current_match_id is not null then
    return jsonb_build_object('status', 'matched', 'match_id', v_p.current_match_id);
  end if;

  insert into public.match_queue (user_id, gender)
  values (v_uid, v_p.gender)
  on conflict (user_id) do update
    set last_heartbeat = now(), gender = excluded.gender;

  return private.try_match(v_uid);
end;
$$;

-- Bekleme ekranı ~5 sn'de bir çağırır: canlılık + yeniden eşleşme denemesi + tahmini süre
create or replace function public.heartbeat_queue()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
begin
  if private.is_banned(v_uid) then
    perform private.kick_user(v_uid);
    return jsonb_build_object('status', 'banned');
  end if;
  return private.try_match(v_uid);
end;
$$;

create or replace function public.leave_queue()
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  delete from public.match_queue where user_id = private.require_uid();
end;
$$;

-- Karşı tarafın SADECE takma adını ve emojisini döner
create or replace function public.get_match(p_match_id uuid)
returns jsonb
language plpgsql stable
security definer
set search_path = ''
as $$
declare
  v_uid     uuid := private.require_uid();
  v_m       public.matches;
  v_partner public.profiles;
begin
  select * into v_m from public.matches
   where id = p_match_id and v_uid in (user_a, user_b);
  if v_m.id is null then
    raise exception 'match_not_found';
  end if;

  select * into v_partner from public.profiles
   where id = case when v_m.user_a = v_uid then v_m.user_b else v_m.user_a end;

  return jsonb_build_object(
    'id',               v_m.id,
    'status',           v_m.status,
    'started_at',       v_m.started_at,
    'ended_at',         v_m.ended_at,
    'ended_by_me',      v_m.ended_by = v_uid,
    'partner_nickname', coalesce(v_partner.nickname, 'Ayrılan kullanıcı'),
    'partner_emoji',    coalesce(v_partner.emoji, '👤')
  );
end;
$$;

create or replace function public.end_match(p_match_id uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := private.require_uid();
begin
  perform 1 from public.matches
   where id = p_match_id and v_uid in (user_a, user_b) and status = 'active'
   for update;
  if found then
    perform private.end_match_internal(p_match_id, v_uid);
  end if;
end;
$$;

-- Sohbetteki kişiyi engelle (ve sohbeti bitir). Bir daha asla eşleşmezsiniz.
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

  insert into public.blocks (blocker_id, blocked_id)
  values (v_uid, v_partner)
  on conflict do nothing;

  perform private.end_match_internal(p_match_id, v_uid);
end;
$$;
