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

-- ── 5. audit_log (permanent — never purged) ──────────────────────────────────
create table if not exists public.audit_log (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  record     jsonb not null default '{}'
);

alter table public.audit_log enable row level security;
drop policy if exists "allow all" on public.audit_log;
create policy "allow all" on public.audit_log for all using (true) with check (true);

-- ── 6. custom_params (persisted custom audit parameters) ─────────────────────
create table if not exists public.custom_params (
  id         text primary key,   -- slug: name lowercased + underscored
  name       text not null,
  options    text not null default 'Yes|No',  -- pipe-separated
  guide      text not null default '',
  input_type text not null default 'dropdown' -- dropdown | scoring | number | text
);

-- migration: add input_type if missing on existing installs
alter table public.custom_params add column if not exists input_type text not null default 'dropdown';

alter table public.custom_params enable row level security;
drop policy if exists "allow all" on public.custom_params;
create policy "allow all" on public.custom_params for all using (true) with check (true);

-- ── 7. pending_audits (QA bulk-upload queue) ─────────────────────────────────
create table if not exists public.pending_audits (
  id           bigint generated always as identity primary key,
  created_at   timestamptz not null default now(),
  assigned_qa  text not null default '',
  status       text not null default 'Ready for Audit',  -- 'Ready for Audit' | 'Completed'
  record       jsonb not null default '{}'
);

alter table public.pending_audits enable row level security;
drop policy if exists "allow all" on public.pending_audits;
create policy "allow all" on public.pending_audits for all using (true) with check (true);

-- ── Verify: list all tables and their RLS status ──────────────────────────────
select
  schemaname,
  tablename,
  rowsecurity as rls_enabled
from pg_tables
where schemaname = 'public'
order by tablename;
