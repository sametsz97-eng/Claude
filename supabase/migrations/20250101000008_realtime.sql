-- 0008: Realtime
-- ---------------------------------------------------------------
-- postgres_changes RLS'e uyar: kullanıcı sadece katıldığı eşleşmelerin
-- matches satırlarını ve mesajlarını alır.
alter publication supabase_realtime add table public.messages, public.matches;
