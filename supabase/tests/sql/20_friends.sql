-- Arkadaşlık testleri: istek/kabul, karşılıklı otomatik kabul, günlük 3 hak,
-- silme, engelleme, RLS ve arkadaş sohbetinden şikâyet.
\set ON_ERROR_STOP 1

create temp table fu (name text primary key, id uuid);
grant select on fu to authenticated;
insert into fu select n, gen_random_uuid()
  from (select 'fk' || i as n from generate_series(1, 6) i
        union all select 'fe' || i from generate_series(1, 6) i) s;
insert into auth.users (id, phone)
select id, '+90 533 000 ' || lpad((row_number() over (order by name))::text, 4, '0') from fu;

do $$
declare r record;
begin
  for r in select * from fu loop
    perform set_config('request.jwt.claim.sub', r.id::text, false);
    perform public.bootstrap_session('fdev-' || r.name);
    perform public.accept_consents('kvkk-v1', true, true);
    perform public.set_gender(case when r.name like 'fk%' then 'female' else 'male' end::public.gender_t);
    perform public.admin_mark_verified(r.id, 'mock', true,
      case when r.name like 'fk%' then 'female' else 'male' end::public.gender_t);
  end loop;
end $$;

-- a ile b arasında (bitmiş) bir eşleşme oluştur, id'sini döndür
create function pg_temp.mk_match(a text, b text) returns uuid language sql as $$
  insert into public.matches (user_a, user_b, status, ended_at)
  values ((select id from fu where name = a), (select id from fu where name = b), 'ended', now())
  returning id
$$;
create temp table fm (k text primary key, id uuid);
grant select on fm to authenticated;
insert into fm values
  ('fk1-fe1', pg_temp.mk_match('fk1', 'fe1')),
  ('fk1-fe2', pg_temp.mk_match('fk1', 'fe2')),
  ('fk1-fe3', pg_temp.mk_match('fk1', 'fe3')),
  ('fk1-fe4', pg_temp.mk_match('fk1', 'fe4')),
  ('fk2-fe1', pg_temp.mk_match('fk2', 'fe1')),
  ('fk3-fe5', pg_temp.mk_match('fk3', 'fe5'));

create function pg_temp.act(p text) returns void language sql as $$
  select set_config('request.jwt.claim.sub', (select id::text from fu where name = p), false)
$$;
create function pg_temp.expect_error(p_sql text, p_code text) returns void language plpgsql as $$
begin
  execute p_sql;
  raise exception 'hata bekleniyordu: %', p_code;
exception when raise_exception then
  if sqlerrm <> p_code then raise exception 'beklenen % ama gelen %', p_code, sqlerrm; end if;
end $$;

set role authenticated;

-- 1) Eşleşmediğin kişinin sohbetine istek atılamaz
select pg_temp.act('fe2');
select pg_temp.expect_error(
  format('select public.send_friend_request(%L)', (select id from fm where k = 'fk3-fe5')),
  'match_not_found');

-- 2) fk1 -> fe1 istek; fe1 kabul eder
select pg_temp.act('fk1');
do $$ declare r jsonb := public.send_friend_request((select id from fm where k = 'fk1-fe1')); begin
  assert r->>'status' = 'sent', r::text;
  assert (r->>'remaining_today')::int = 2, 'kalan hak 2 olmalı: ' || r::text;
end $$;
select pg_temp.expect_error(
  format('select public.send_friend_request(%L)', (select id from fm where k = 'fk1-fe1')),
  'friend_request_pending');

select pg_temp.act('fe1');
do $$
declare o jsonb := public.get_friends_overview();
begin
  assert jsonb_array_length(o->'incoming') = 1, 'fe1 bir istek görmeli: ' || o::text;
  perform public.respond_friend_request((o->'incoming'->0->>'request_id')::uuid, true);
  o := public.get_friends_overview();
  assert jsonb_array_length(o->'friends') = 1, 'fe1 bir arkadaş görmeli';
  assert jsonb_array_length(o->'incoming') = 0;
end $$;

-- 3) Arkadaş mesajlaşması ve RLS
select pg_temp.act('fk1');
insert into public.friend_messages (friendship_id, sender_id, body)
select (public.get_friends_overview()->'friends'->0->>'friendship_id')::uuid, auth.uid(), 'Selam arkadaşım';
select pg_temp.act('fe1');
do $$ begin
  assert (select count(*) from public.friend_messages) = 1, 'fe1 mesajı görmeli';
  assert public.get_friends_overview()->'friends'->0->>'last_message' = 'Selam arkadaşım';
end $$;
reset role;
create temp table ff as select id from public.friendships
  where user_a = least((select id from fu where name = 'fk1'), (select id from fu where name = 'fe1'))
    and user_b = greatest((select id from fu where name = 'fk1'), (select id from fu where name = 'fe1'));
grant select on ff to authenticated;
set role authenticated;
select pg_temp.act('fe2');
do $$ begin
  assert (select count(*) from public.friend_messages) = 0, 'yabancı arkadaş mesajı görmemeli';
  begin
    insert into public.friend_messages (friendship_id, sender_id, body)
    select id, auth.uid(), 'sızma' from ff;
    raise exception 'yabancı arkadaş sohbetine yazmamalı';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.friendships (user_a, user_b)
    values (least(auth.uid(), (select id from fu where name = 'fk1')),
            greatest(auth.uid(), (select id from fu where name = 'fk1')));
    raise exception 'doğrudan arkadaşlık eklenmemeli';
  exception when insufficient_privilege then null; end;
end $$;

-- 4) Zaten arkadaş -> tekrar istek yok
select pg_temp.act('fe1');
select pg_temp.expect_error(
  format('select public.send_friend_request(%L)', (select id from fm where k = 'fk1-fe1')),
  'already_friends');

-- 5) Karşılıklı istek -> otomatik kabul (fe2 -> fk1, sonra fk1 -> fe2)
select pg_temp.act('fe2');
select public.send_friend_request((select id from fm where k = 'fk1-fe2'));
select pg_temp.act('fk1');
do $$ declare r jsonb := public.send_friend_request((select id from fm where k = 'fk1-fe2')); begin
  assert r->>'status' = 'accepted', 'karşılıklı istek otomatik kabul edilmeli: ' || r::text;
  assert (r->>'remaining_today')::int = 1, 'fk1 bugün 2 istek kullandı: ' || r::text;
end $$;

-- 6) Günlük limit: 3. istek olur, 4. olmaz
select public.send_friend_request((select id from fm where k = 'fk1-fe3'));
select pg_temp.expect_error(
  format('select public.send_friend_request(%L)', (select id from fm where k = 'fk1-fe4')),
  'friend_daily_limit');
do $$ begin
  assert (public.get_friends_overview()->>'remaining_today')::int = 0;
end $$;

-- 7) Silme: fk1, fe1'i siler -> iki taraftan da kalkar, mesajlar silinir; hak geri gelmez
do $$ begin
  perform public.remove_friend((select id from ff));
  assert jsonb_array_length(public.get_friends_overview()->'friends') = 1, 'fk1: sadece fe2 kalmalı';
  assert (public.get_friends_overview()->>'remaining_today')::int = 0, 'silme hakkı geri vermemeli';
end $$;
select pg_temp.act('fe1');
do $$ begin
  assert jsonb_array_length(public.get_friends_overview()->'friends') = 0, 'fe1 tarafında da silinmeli';
  assert (select count(*) from public.friend_messages) = 0, 'mesaj geçmişi silinmeli';
  begin
    insert into public.friend_messages (friendship_id, sender_id, body) select id, auth.uid(), 'x' from ff;
    raise exception 'silinen arkadaşa yazılmamalı';
  exception when insufficient_privilege then null; end;
end $$;

-- Silinen arkadaş, yeni bir istekle tekrar eklenebilir
do $$ declare r jsonb := public.send_friend_request((select id from fm where k = 'fk1-fe1')); begin
  assert r->>'status' = 'sent', r::text;
end $$;

-- 8) Engelleme: fe1, fk2 ile arkadaş olur; sonra fk2 engeller -> arkadaşlık kalkar, istek atılamaz
select pg_temp.act('fe1');
select public.send_friend_request((select id from fm where k = 'fk2-fe1'));
select pg_temp.act('fk2');
do $$
declare o jsonb := public.get_friends_overview();
begin
  perform public.respond_friend_request((o->'incoming'->0->>'request_id')::uuid, true);
  o := public.get_friends_overview();
  assert jsonb_array_length(o->'friends') = 1;
  perform public.block_friend((o->'friends'->0->>'friendship_id')::uuid);
  assert jsonb_array_length(public.get_friends_overview()->'friends') = 0, 'engellenince arkadaşlık kalkmalı';
end $$;
select pg_temp.act('fe1');
select pg_temp.expect_error(
  format('select public.send_friend_request(%L)', (select id from fm where k = 'fk2-fe1')),
  'friend_blocked');

-- 9) Reddetme
select pg_temp.act('fe5');
select public.send_friend_request((select id from fm where k = 'fk3-fe5'));
select pg_temp.act('fk3');
do $$
declare o jsonb := public.get_friends_overview();
begin
  perform public.respond_friend_request((o->'incoming'->0->>'request_id')::uuid, false);
  o := public.get_friends_overview();
  assert jsonb_array_length(o->'incoming') = 0 and jsonb_array_length(o->'friends') = 0, 'reddedilmeli';
end $$;

-- 10) Arkadaş sohbetinden şikâyet: sayaca işlenir, arkadaşlık kalkar
select pg_temp.act('fe5');
select public.send_friend_request((select id from fm where k = 'fk3-fe5'));
select pg_temp.act('fk3');
do $$
declare o jsonb := public.get_friends_overview(); r jsonb;
begin
  perform public.respond_friend_request((o->'incoming'->0->>'request_id')::uuid, true);
  o := public.get_friends_overview();
  r := public.report_friend((o->'friends'->0->>'friendship_id')::uuid, 'harassment', null);
  assert (r->>'counted')::boolean, 'şikâyet sayılmalı';
  assert jsonb_array_length(public.get_friends_overview()->'friends') = 0, 'şikâyet arkadaşlığı kaldırmalı';
end $$;
reset role;
do $$ begin
  assert exists (select 1 from private.reports r join fu on fu.id = r.reported_user_id
                  where fu.name = 'fe5' and r.category = 'harassment'), 'şikâyet deftere yazılmalı';
end $$;

\echo 'arkadaşlık testleri OK'
