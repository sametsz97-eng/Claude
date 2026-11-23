-- Uçtan uca akış testi: onboarding, eşleşme, engelleme, mesaj RLS, şikâyet/ban.
\set ON_ERROR_STOP 1

insert into private.app_config values ('hash_pepper', repeat('x', 40));

-- Kullanıcılar: k1..k3 kız, e1..e12 erkek
create temp table u (name text primary key, id uuid);
grant select on u to authenticated;
insert into u
select n, gen_random_uuid() from (
  select 'k' || i as n from generate_series(1, 3) i
  union all select 'e' || i from generate_series(1, 12) i) s;
insert into auth.users (id, phone) select id, '+90 555 000 ' || lpad((row_number() over ())::text, 4, '0') from u;

-- Kullanıcı olarak davran
create function pg_temp.act(p_name text) returns void language plpgsql as $$
begin
  perform set_config('request.jwt.claim.sub', (select id::text from u where name = p_name), false);
end $$;

-- Herkesi onboard et (kızlar k*, erkekler e*), doğrulamayı service_role ile işaretle
do $$
declare r record;
begin
  for r in select * from u loop
    perform set_config('request.jwt.claim.sub', r.id::text, false);
    set local role authenticated;
    perform public.bootstrap_session('device-' || r.name);
    perform public.accept_consents('kvkk-v1', true, true);
    perform public.set_gender(case when r.name like 'k%' then 'female' else 'male' end::public.gender_t);
    reset role;
    set local role service_role;
    perform public.admin_mark_verified(r.id, 'mock', true,
      case when r.name like 'k%' then 'female' else 'male' end::public.gender_t);
    reset role;
  end loop;
end $$;

do $$ begin
  assert (select count(*) from public.profiles where gender_verified) = 15, 'herkes doğrulanmış olmalı';
  assert (select count(*) from private.identities) = 15, 'kimlik hash kayıtları';
  assert not exists (select 1 from private.identities where phone_hash like '%555%'), 'numara açık metin olmamalı';
end $$;

-- authenticated doğrudan profil güncelleyemez / private okuyamaz
set role authenticated;
select pg_temp.act('e1');
do $$ begin
  begin
    update public.profiles set gender_verified = true;
    raise exception 'UPDATE engellenmeliydi';
  exception when insufficient_privilege then null; end;
  begin
    perform 1 from private.bans;
    raise exception 'private okunmamalıydı';
  exception when insufficient_privilege then null; end;
  begin
    perform public.admin_mark_verified(auth.uid(), 'mock', true, 'male');
    raise exception 'admin fonksiyonu çağrılmamalıydı';
  exception when insufficient_privilege then null; end;
  assert (select count(*) from public.profiles) = 1, 'sadece kendi profilini görmeli';
end $$;
reset role;

-- Eşleşme: 3 erkek kuyruğa, sonra 1 kız -> en eski erkekle eşleşir
set role authenticated;
select pg_temp.act('e1'); select public.join_queue();
select pg_temp.act('e2'); select public.join_queue();
select pg_temp.act('e3');
do $$ declare s jsonb := public.join_queue(); begin
  assert s->>'status' = 'waiting', 'e3 beklemeli';
  assert (s->>'position')::int = 3, 'e3 3. sırada olmalı: ' || s::text;
  assert (s->>'eta_seconds')::int > 0, 'tahmini süre olmalı';
end $$;
select pg_temp.act('k1');
do $$ declare s jsonb := public.join_queue(); begin
  assert s->>'status' = 'matched', 'k1 eşleşmeli: ' || s::text;
end $$;
reset role;

do $$ begin
  assert exists (select 1 from public.matches m join u a on a.id = m.user_a join u b on b.id = m.user_b
                  where a.name = 'k1' and b.name = 'e1' and m.status = 'active'), 'k1-e1 eşleşmeli';
  assert (select count(*) from public.match_queue) = 2, 'kuyrukta e2,e3 kalmalı';
end $$;

-- Mesajlaşma RLS
set role authenticated;
select pg_temp.act('k1');
insert into public.messages (match_id, sender_id, body)
select current_match_id, id, 'Merhaba!' from public.profiles;
reset role;
create temp table k1match as select current_match_id as id from public.profiles where id = (select id from u where name = 'k1');
grant select on k1match to authenticated;
set role authenticated;
select pg_temp.act('e2');
do $$ begin
  assert (select count(*) from public.messages) = 0, 'e2 başkasının mesajını görmemeli';
  begin
    insert into public.messages (match_id, sender_id, body) select id, auth.uid(), 'sızma' from k1match;
    raise exception 'yabancı sohbete mesaj atılmamalı';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.messages (match_id, sender_id, body)
    select id, (select id from u where name = 'k1'), 'taklit' from k1match;
    raise exception 'başkası adına mesaj atılmamalı';
  exception when insufficient_privilege then null; end;
end $$;
select pg_temp.act('e1');
do $$ begin
  assert (select count(*) from public.messages) = 1, 'e1 mesajı görmeli';
  assert (public.get_match((select current_match_id from public.profiles))->>'partner_nickname') is not null;
end $$;

-- e1 engeller -> sohbet biter, bir daha eşleşmezler
select public.block_partner((select current_match_id from public.profiles));
select public.join_queue();          -- e1 tekrar kuyrukta
select pg_temp.act('k1');
do $$ begin
  assert (select current_match_id from public.profiles) is null, 'sohbet bitmeli';
end $$;
do $$ declare s jsonb := public.join_queue(); begin
  -- k1, e1'i atlamalı (engel) ve e2 ile eşleşmeli
  assert s->>'status' = 'matched', 'k1 tekrar eşleşmeli';
end $$;
reset role;
do $$ begin
  assert exists (select 1 from public.matches m join u b on b.id = m.user_b join u a on a.id = m.user_a
                  where m.status = 'active' and a.name = 'k1' and b.name = 'e2'), 'k1-e2 eşleşmeli (e1 engelli)';
end $$;

-- Art arda aynı kişi yok: k1-e2 biter, sadece e2 kuyruktayken k1 eşleşmemeli
delete from public.match_queue;
set role authenticated;
select pg_temp.act('k1'); select public.end_match((select current_match_id from public.profiles));
select pg_temp.act('e2'); select public.join_queue();
select pg_temp.act('k1');
do $$ declare s jsonb := public.join_queue(); begin
  assert s->>'status' = 'waiting', 'son partnerle tekrar eşleşmemeli: ' || s::text;
end $$;
select public.leave_queue();
select pg_temp.act('e2'); select public.leave_queue();
reset role;

-- Şikâyet: k2, e4..e12 ile eşleşip her birinin k2'yi şikâyet etmesi
-- (k2 kadın; şikâyet edenler 9 farklı erkek)
create function pg_temp.match_and_report(p_reporter text, p_target text, p_cat public.report_category_t)
returns jsonb language plpgsql as $$
declare v_mid uuid;
begin
  -- eşleşmeyi doğrudan oluştur (test kısayolu)
  insert into public.matches (user_a, user_b)
  values ((select id from u where name = p_reporter), (select id from u where name = p_target))
  returning id into v_mid;
  update public.profiles set current_match_id = v_mid
   where id in ((select id from u where name = p_reporter), (select id from u where name = p_target));
  perform set_config('request.jwt.claim.sub', (select id::text from u where name = p_reporter), false);
  set local role authenticated;
  return public.report_partner(v_mid, p_cat, 'test');
end $$;

begin;
select pg_temp.match_and_report('e4', 'k2', 'profanity');
commit;
begin;
select pg_temp.match_and_report('e4', 'k2', 'profanity');  -- aynı kişi: sayılmamalı
commit;
begin; select pg_temp.match_and_report('e5', 'k2', 'gender_mismatch'); commit;
do $$ begin
  assert (select count(*) from private.reports) = 2, 'aynı kişiden 2. şikâyet sayılmamalı';
  assert not private.is_banned((select id from u where name = 'k2')), '2 şikâyette ban yok';
end $$;
begin; select pg_temp.match_and_report('e6', 'k2', 'gender_mismatch'); commit;
do $$
declare b private.bans := private.active_ban((select id from u where name = 'k2'));
begin
  assert b.id is not null, '3 şikâyette ban olmalı';
  assert b.expires_at between now() + interval '23 hours' and now() + interval '25 hours', '24 saat olmalı';
  assert exists (select 1 from private.bans where device_hash is not null and reason = 'reports_level1'), 'cihaz banı';
  assert (select gender_verified from public.profiles p join u on u.id = p.id where u.name = 'k2'),
    'sadece 2 cinsiyet şikâyeti: henüz yeniden doğrulama yok';
end $$;

-- Banlı kullanıcı kuyruğa giremez ve mesaj atamaz
set role authenticated;
select pg_temp.act('k2');
do $$ begin
  begin perform public.join_queue(); raise exception 'banlı kuyruğa girmemeli';
  exception when raise_exception then
    if sqlerrm <> 'banned' then raise; end if;
  end;
  assert (public.bootstrap_session('device-k2')->>'banned')::boolean, 'bootstrap banlı dönmeli';
end $$;
reset role;

-- Aynı cihazla yeni hesap açan kişi de banlı olmalı
insert into u values ('k2b', gen_random_uuid());
insert into auth.users (id, phone) select id, '+90 555 999 9999' from u where name = 'k2b';
set role authenticated;
select pg_temp.act('k2b');
do $$ begin
  assert (public.bootstrap_session('device-k2')->>'banned')::boolean, 'cihaz banı yeni hesaba da uygulanmalı';
end $$;
reset role;

-- 3. cinsiyet şikâyeti -> yeniden doğrulama
begin; select pg_temp.match_and_report('e7', 'k2', 'gender_mismatch'); commit;
do $$ begin
  assert (select needs_reverification and not gender_verified
            from public.profiles p join u on u.id = p.id where u.name = 'k2'), 'yeniden doğrulama gerekmeli';
end $$;

begin; select pg_temp.match_and_report('e8', 'k2', 'harassment'); commit;
begin; select pg_temp.match_and_report('e9', 'k2', 'nsfw'); commit;  -- 6
do $$
declare b private.bans := private.active_ban((select id from u where name = 'k2'));
begin
  assert b.expires_at > now() + interval '6 days', '6 şikâyette 7 gün olmalı';
end $$;
begin; select pg_temp.match_and_report('e10', 'k2', 'nsfw'); commit;
begin; select pg_temp.match_and_report('e11', 'k2', 'nsfw'); commit;
begin; select pg_temp.match_and_report('e12', 'k2', 'nsfw'); commit;  -- 9
do $$
declare b private.bans := private.active_ban((select id from u where name = 'k2'));
begin
  assert b.id is not null and b.expires_at is null, '9 şikâyette kalıcı ban olmalı';
end $$;

-- Hesap silinip aynı numarayla yeniden açılsa da ban sürer
create temp table k2phone as select phone from auth.users where id = (select id from u where name = 'k2');
set role authenticated;
select pg_temp.act('k2');
select public.delete_account();
reset role;
do $$ begin
  assert not exists (select 1 from public.profiles p join u on u.id = p.id where u.name = 'k2'), 'profil silinmeli';
end $$;
insert into u values ('k2c', gen_random_uuid());
insert into auth.users (id, phone) select (select id from u where name = 'k2c'), phone from k2phone;
set role authenticated;
select pg_temp.act('k2c');
do $$ declare s jsonb := public.bootstrap_session('yeni-cihaz'); begin
  assert (s->>'banned')::boolean and (s->>'ban_permanent')::boolean, 'aynı numara kalıcı banlı olmalı: ' || s::text;
end $$;
reset role;

\echo 'flow testleri OK'
