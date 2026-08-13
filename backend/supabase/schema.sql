-- ============================================================
-- 사장님 콘텐츠비서 Supabase Schema
-- Run this in Supabase SQL Editor
-- ============================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- ─── users ────────────────────────────────────────────────
create table if not exists users (
  id          uuid primary key default auth.uid(),
  email       text unique not null,
  plan        text not null default 'free',  -- 'free' | 'pro'
  created_at  timestamptz not null default now()
);

alter table users enable row level security;

create policy "users can read own row"
  on users for select using (auth.uid() = id);

create policy "users can update own row"
  on users for update using (auth.uid() = id);

-- ─── places ───────────────────────────────────────────────
create table if not exists places (
  id            uuid primary key default uuid_generate_v4(),
  user_id       uuid references users(id) on delete cascade,
  place_url     text not null,
  business_name text,
  category      text,
  region        text,
  raw_text      text,
  created_at    timestamptz not null default now()
);

alter table places enable row level security;

create policy "users can read own places"
  on places for select using (auth.uid() = user_id);

create policy "users can insert own places"
  on places for insert with check (auth.uid() = user_id);

-- ─── generations ──────────────────────────────────────────
create table if not exists generations (
  id             uuid primary key default uuid_generate_v4(),
  user_id        uuid references users(id) on delete cascade,
  place_id       uuid references places(id) on delete set null,
  place_url      text,
  analysis_json  jsonb,
  content_json   jsonb,
  bonus_json     jsonb,
  created_at     timestamptz not null default now()
);

alter table generations enable row level security;

create policy "users can read own generations"
  on generations for select using (auth.uid() = user_id);

create policy "users can insert own generations"
  on generations for insert with check (auth.uid() = user_id);

-- Allow anonymous inserts for MVP (Phase 1 — no auth required)
create policy "anon can insert generations"
  on generations for insert to anon with check (user_id is null);

create policy "anon can read anon generations"
  on generations for select to anon using (user_id is null);

-- ─── usage_logs ───────────────────────────────────────────
create table if not exists usage_logs (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid references users(id) on delete cascade,
  action      text not null,          -- 'generate' | 'modify' | 'save'
  token_used  integer not null default 0,
  created_at  timestamptz not null default now()
);

alter table usage_logs enable row level security;

create policy "users can read own usage"
  on usage_logs for select using (auth.uid() = user_id);

create policy "users can insert own usage"
  on usage_logs for insert with check (auth.uid() = user_id);

create policy "anon can insert usage"
  on usage_logs for insert to anon with check (user_id is null);

-- ─── Indexes ──────────────────────────────────────────────
create index if not exists idx_generations_created_at on generations(created_at desc);
create index if not exists idx_usage_logs_created_at  on usage_logs(created_at desc);
create index if not exists idx_generations_user_id    on generations(user_id);
