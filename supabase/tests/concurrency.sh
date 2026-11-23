#!/usr/bin/env bash
# 30 kız + 30 erkek aynı anda kuyruğa girer; heartbeat'lerle herkes eşleşmeli,
# kimse iki sohbette birden olmamalı. run_local.sh tarafından çağrılır.
set -euo pipefail
N=30
$PSQL -d t <<SQL
create table public.cc_users (id uuid primary key, g public.gender_t);
insert into public.cc_users select gen_random_uuid(), case when i % 2 = 0 then 'female' else 'male' end::public.gender_t
  from generate_series(1, $((N*2))) i;
insert into auth.users (id, phone) select id, '+90 444 ' || lpad(row_number() over ()::text, 7, '0') from public.cc_users;
do \$\$ declare r record; begin
  for r in select * from public.cc_users loop
    perform set_config('request.jwt.claim.sub', r.id::text, false);
    perform public.bootstrap_session(null);
    perform public.accept_consents('kvkk-v1', true, true);
    perform public.set_gender(r.g);
    perform public.admin_mark_verified(r.id, 'mock', true, r.g);
  end loop;
end \$\$;
SQL
ids=$($PSQL -d t -At -c "select id from public.cc_users")
pids=()
for id in $ids; do
  (
    $PSQL -d t -At >/dev/null <<SQL
set role authenticated;
select set_config('request.jwt.claim.sub', '$id', false);
select public.join_queue();
select pg_sleep(random() * 0.2);
select public.heartbeat_queue();
select pg_sleep(random() * 0.2);
select public.heartbeat_queue();
select public.heartbeat_queue();
SQL
  ) &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
# Son bir heartbeat turu (skip-locked nedeniyle beklemede kalanlar için)
for id in $ids; do
  $PSQL -d t -At >/dev/null -c "set role authenticated; select set_config('request.jwt.claim.sub', '$id', false); select public.heartbeat_queue();"
done
$PSQL -d t <<'SQL'
do $$
declare v_matches int; v_dupes int; v_mixed int;
begin
  select count(*) into v_matches from public.matches m
    join public.cc_users a on a.id = m.user_a where m.status = 'active';
  select count(*) into v_dupes from (
    select uid from (select user_a uid from public.matches where status = 'active'
                     union all select user_b from public.matches where status = 'active') x
    group by uid having count(*) > 1) d;
  select count(*) into v_mixed from public.matches m
    join public.profiles a on a.id = m.user_a join public.profiles b on b.id = m.user_b
   where m.status = 'active' and a.gender = b.gender;
  assert v_dupes = 0, 'bir kullanıcı iki aktif sohbette: ' || v_dupes;
  assert v_mixed = 0, 'aynı cinsiyet eşleşmesi var';
  assert v_matches = 30, 'herkes eşleşmeliydi, eşleşme sayısı: ' || v_matches;
  assert (select count(*) from public.profiles p join public.cc_users c on c.id = p.id
           where p.current_match_id is null) = 0, 'eşleşmeyen kaldı';
end $$;
drop table public.cc_users;
SQL
echo "eşzamanlılık testi OK"
