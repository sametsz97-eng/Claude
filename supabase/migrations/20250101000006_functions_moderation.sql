-- 0006: Şikâyet ve kademeli ban
-- ---------------------------------------------------------------
-- Kurallar:
--  * "Kişi" telefon numarasıdır (hash). Aynı kişi şikâyet edilen kişiyi
--    ömür boyu yalnızca bir kez şikâyet edebilir; ikinci şikâyet sayılmaz.
--  * Sayaç ömür boyudur (hesap silinip açılsa da sıfırlanmaz).
--  * 3 farklı kişi  -> 24 saat ban
--    6 farklı kişi  -> 7 gün ban
--    9 farklı kişi  -> kalıcı ban
--  * "Cinsiyeti farklı": son doğrulamadan sonra 3 farklı kişiden gelirse
--    yeniden selfie doğrulaması zorunlu olur. Bu şikâyetler ban sayacına da dahildir.
--  * Şikâyet eden kişi şikâyet edileni otomatik engeller ve sohbet biter.

create or replace function public.report_partner(
  p_match_id uuid, p_category public.report_category_t, p_note text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid           uuid := private.require_uid();
  v_m             public.matches;
  v_partner       uuid;
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

  select * into v_m from public.matches
   where id = p_match_id and v_uid in (user_a, user_b);
  if v_m.id is null then
    raise exception 'match_not_found';
  end if;
  v_partner := case when v_m.user_a = v_uid then v_m.user_b else v_m.user_a end;

  select phone_hash into v_reporter_hash from private.identities where user_id = v_uid;
  select phone_hash into v_reported_hash from private.identities where user_id = v_partner;
  if v_reporter_hash is null or v_reported_hash is null then
    raise exception 'identity_missing';
  end if;

  -- Önce engelle + sohbeti bitir (kilit sırası: kuyruk yok, matches -> profiles)
  insert into public.blocks (blocker_id, blocked_id)
  values (v_uid, v_partner) on conflict do nothing;
  perform private.end_match_internal(p_match_id, v_uid);

  if v_reporter_hash = v_reported_hash then
    -- aynı telefonun iki hesabı; sayılmaz
    return jsonb_build_object('counted', false);
  end if;

  -- Aynı şikâyet edilen kişi için şikâyetleri seri hâle getir (sayaç yarışı önlemi)
  perform pg_advisory_xact_lock(hashtextextended('report:' || v_reported_hash, 0));

  insert into private.reports (
    reporter_user_id, reported_user_id, reporter_phone_hash, reported_phone_hash,
    match_id, category, note)
  values (
    v_uid, v_partner, v_reporter_hash, v_reported_hash,
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
      perform private.apply_ban(v_partner, null, 'reports_permanent');
    end if;
  elsif v_total = 6 then
    perform private.apply_ban(v_partner, interval '7 days', 'reports_level2');
  elsif v_total = 3 then
    perform private.apply_ban(v_partner, interval '24 hours', 'reports_level1');
  end if;

  if p_category = 'gender_mismatch' then
    select verified_at into v_verified_at from public.profiles where id = v_partner;
    select count(distinct reporter_phone_hash) into v_gm
      from private.reports
     where reported_phone_hash = v_reported_hash
       and category = 'gender_mismatch'
       and created_at > coalesce(v_verified_at, '-infinity'::timestamptz);
    if v_gm >= 3 then
      perform private.require_reverification(v_partner);
    end if;
  end if;

  return jsonb_build_object('counted', true);
end;
$$;

-- Mesaj gönderimine basit hız sınırı ve sunucu zamanı
create or replace function private.messages_before_insert()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.created_at := now();
  new.body := btrim(new.body);
  if (select count(*) from public.messages
       where sender_id = new.sender_id
         and created_at > now() - interval '10 seconds') >= 15 then
    raise exception 'rate_limited';
  end if;
  return new;
end;
$$;

create trigger messages_before_insert
before insert on public.messages
for each row execute function private.messages_before_insert();
