-- Run this entire file in: Supabase Dashboard → SQL Editor → New query
-- Safe to re-run: uses IF NOT EXISTS and DROP POLICY IF EXISTS

-- ── 1. clients ────────────────────────────────────────────────────────────────
create table if not exists public.clients (
  id          text primary key,
  company     text not null default '',
  contact     text not null default '',
  emails      text not null default '',   -- pipe-separated list
  status      text not null default 'Active',
  tags        text not null default '',   -- pipe-separated list
  notes       text not null default '',
  added_at    text not null default ''
);

alter table public.clients enable row level security;
drop policy if exists "allow all" on public.clients;
create policy "allow all" on public.clients for all using (true) with check (true);

-- ── 2. sent_items ─────────────────────────────────────────────────────────────
create table if not exists public.sent_items (
  id              text primary key,
  timestamp       text not null default '',
  date            text not null default '',
  time            text not null default '',
  sender          text not null default '',
  draft_name      text not null default '',
  subject         text not null default '',
  template_num    integer not null default 1,
  template_name   text not null default '',
  client          text not null default '',
  attachment_name text not null default '',
  is_test         boolean not null default false,
  sent_to         text not null default '',   -- pipe-separated list
  failed          jsonb not null default '[]',
  body_preview    text not null default ''
);

alter table public.sent_items enable row level security;
drop policy if exists "allow all" on public.sent_items;
create policy "allow all" on public.sent_items for all using (true) with check (true);

-- ── 3. tracking_events ────────────────────────────────────────────────────────
create table if not exists public.tracking_events (
  id          bigint generated always as identity primary key,
  record_id   text not null,
  email       text not null,
  type        text not null,   -- 'open' | 'click' | 'rating'
  rating      integer,
  timestamp   text not null default '',
  date        text not null default '',
  time        text not null default ''
);

alter table public.tracking_events enable row level security;
drop policy if exists "allow all" on public.tracking_events;
create policy "allow all" on public.tracking_events for all using (true) with check (true);

-- ── 4. client_emails  (MISSING — root cause of history not persisting) ────────
create table if not exists public.client_emails (
  id              text primary key,
  client_company  text not null default '',
  date            text not null default '',
  subject         text not null default '',
  template_name   text not null default '',
  sent_to         text not null default '',   -- pipe-separated list
  body_preview    text not null default '',
  sender          text not null default '',
  attachment_name text not null default ''
);

alter table public.client_emails enable row level security;
drop policy if exists "allow all" on public.client_emails;
create policy "allow all" on public.client_emails for all using (true) with check (true);

-- ── Verify: list all tables and their RLS status ──────────────────────────────
select
  schemaname,
  tablename,
  rowsecurity as rls_enabled
from pg_tables
where schemaname = 'public'
order by tablename;
