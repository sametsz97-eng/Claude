-- 0007: Row Level Security ve yetkiler
-- ---------------------------------------------------------------
-- Prensip: istemci (authenticated) neredeyse hiçbir tabloya doğrudan YAZAMAZ.
-- Tüm durum değişiklikleri SECURITY DEFINER RPC'ler üzerinden yapılır.
-- Tek istisna: messages tablosuna INSERT (RLS ile korunur).

-- ---------- RLS'i aç ----------
alter table public.profiles    enable row level security;
alter table public.consents    enable row level security;
alter table public.match_queue enable row level security;
alter table public.matches     enable row level security;
alter table public.messages    enable row level security;
alter table public.blocks      enable row level security;

-- ---------- Tablo yetkileri ----------
revoke all on all tables in schema public from anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;

grant select on public.profiles, public.consents, public.match_queue,
                public.matches, public.messages, public.blocks to authenticated;
grant insert (match_id, sender_id, body) on public.messages to authenticated;

-- ---------- Politikalar ----------
-- profiles: sadece kendi satırın. Karşı tarafın takma adı get_match() ile gelir.
create policy profiles_select_own on public.profiles
  for select to authenticated
  using (id = (select auth.uid()));

create policy consents_select_own on public.consents
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy match_queue_select_own on public.match_queue
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy matches_select_participant on public.matches
  for select to authenticated
  using ((select auth.uid()) in (user_a, user_b));

create policy messages_select_participant on public.messages
  for select to authenticated
  using (exists (
    select 1 from public.matches m
     where m.id = messages.match_id
       and (select auth.uid()) in (m.user_a, m.user_b)));

create policy messages_insert_participant on public.messages
  for insert to authenticated
  with check (
    sender_id = (select auth.uid())
    and exists (
      select 1 from public.matches m
       where m.id = messages.match_id
         and m.status = 'active'
         and (select auth.uid()) in (m.user_a, m.user_b))
    and not private.is_banned((select auth.uid()))
  );

create policy blocks_select_own on public.blocks
  for select to authenticated
  using (blocker_id = (select auth.uid()));

-- ---------- private şeması ----------
-- RLS politikasının private.is_banned'ı çağırabilmesi için usage + execute.
-- (private şeması PostgREST'te yayınlanmadığı için API'den çağrılamaz.)
grant usage on schema private to authenticated;
revoke execute on all functions in schema private from public, anon, authenticated;
grant execute on function private.is_banned(uuid) to authenticated;

-- ---------- RPC yetkileri ----------
revoke execute on all functions in schema public from public, anon, authenticated;

grant execute on function
  public.bootstrap_session(text),
  public.get_session_state(),
  public.accept_consents(text, boolean, boolean),
  public.reroll_nickname(),
  public.set_gender(public.gender_t),
  public.delete_account(),
  public.join_queue(),
  public.heartbeat_queue(),
  public.leave_queue(),
  public.get_match(uuid),
  public.end_match(uuid),
  public.block_partner(uuid),
  public.report_partner(uuid, public.report_category_t, text)
to authenticated;

grant execute on function
  public.admin_mark_verified(uuid, text, boolean, public.gender_t),
  public.admin_ban(uuid, int, text)
to service_role;

-- Bundan sonra eklenecek fonksiyonlar varsayılan olarak herkese açılmasın
alter default privileges in schema public revoke execute on functions from public, anon, authenticated;
