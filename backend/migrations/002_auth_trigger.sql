-- FindBack AI — Phase 1: Supabase Auth <-> profile sync
-- Run this AFTER 001_init.sql, once AUTH_MODE=supabase is in use.
--
-- Supabase Auth manages its own `auth.users` table (email, password hash,
-- confirmation state, etc.) which this app never touches directly. This
-- trigger keeps the app's `public.users` profile row (role, name, and — via
-- FK — everything reports/matches/notifications reference) in sync the
-- moment a new auth user is created, so app code never has to.

create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email, name, role)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data ->> 'name',
    'User'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function public.handle_new_auth_user();

-- Tie the profile row's lifecycle to the auth user's lifecycle: deleting a
-- user in Supabase Auth cascades to their profile (and from there, via the
-- existing FKs in 001_init.sql, to their reports/matches/notifications).
alter table public.users
  drop constraint if exists users_id_fkey,
  add constraint users_id_fkey foreign key (id) references auth.users(id) on delete cascade;

-- ---------------------------------------------------------------------
-- Promoting a user to Admin (SRS Section 2) is a manual, deliberate action
-- — never exposed via any API route. Run directly in the Supabase SQL
-- editor when needed:
--
--   update public.users set role = 'Admin' where email = 'someone@example.com';
-- ---------------------------------------------------------------------
