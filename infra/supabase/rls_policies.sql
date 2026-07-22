-- =============================================================================
-- CyberComplyIT — Row Level Security (RLS)
-- Fase 2 della roadmap tecnica: "Configurare Row Level Security (RLS) su Supabase:
-- ogni org vede solo i propri dati".
--
-- QUANDO ESEGUIRE QUESTO SCRIPT
-- Questo script usa la funzione `auth.uid()`, disponibile solo su un progetto Supabase
-- reale (non su un Postgres locale generico: per questo NON fa parte delle migration
-- Alembic, che devono girare identiche sia in locale sia su Supabase). Vai su
-- Supabase → SQL Editor del tuo progetto e incolla ed esegui questo file per intero,
-- dopo aver applicato le migration Alembic (che creano le tabelle).
--
-- COSA PROTEGGE E COSA NO
-- Il backend FastAPI si connette con la Service Role Key, che by design BYPASSA la RLS
-- (necessario perché il backend deve poter leggere/scrivere per conto di qualunque utente
-- dopo aver verificato l'autorizzazione a livello applicativo). La RLS qui serve come
-- seconda linea di difesa per qualunque accesso che passi direttamente da Supabase con la
-- Anon Key o con il JWT dell'utente (es. query dirette da un client Supabase futuro, o
-- l'editor Supabase Studio usato da un membro del team): senza queste policy, con la
-- Anon Key chiunque autenticato potrebbe leggere i dati di TUTTE le organizzazioni.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Funzioni di supporto
-- -----------------------------------------------------------------------------
create schema if not exists private;

create or replace function private.is_org_member(target_org_id uuid)
returns boolean
language sql
security definer
stable
as $$
  select exists (
    select 1
    from public.organization_members m
    where m.organization_id = target_org_id
      and m.user_id = auth.uid()
  );
$$;

create or replace function private.is_org_admin(target_org_id uuid)
returns boolean
language sql
security definer
stable
as $$
  select exists (
    select 1
    from public.organization_members m
    where m.organization_id = target_org_id
      and m.user_id = auth.uid()
      and m.role = 'admin'
  );
$$;

-- -----------------------------------------------------------------------------
-- users — un utente vede se stesso e i membri delle proprie organizzazioni
-- (necessario per mostrare la lista "Membri del team" in Fase 4)
-- -----------------------------------------------------------------------------
alter table public.users enable row level security;

drop policy if exists users_select_self_or_org_peers on public.users;
create policy users_select_self_or_org_peers on public.users
  for select using (
    id = auth.uid()
    or id in (
      select m2.user_id
      from public.organization_members m1
      join public.organization_members m2 on m2.organization_id = m1.organization_id
      where m1.user_id = auth.uid()
    )
  );

drop policy if exists users_update_self on public.users;
create policy users_update_self on public.users
  for update using (id = auth.uid());

-- -----------------------------------------------------------------------------
-- organizations
-- -----------------------------------------------------------------------------
alter table public.organizations enable row level security;

drop policy if exists organizations_select_member on public.organizations;
create policy organizations_select_member on public.organizations
  for select using (private.is_org_member(id));

drop policy if exists organizations_update_admin on public.organizations;
create policy organizations_update_admin on public.organizations
  for update using (private.is_org_admin(id));

-- -----------------------------------------------------------------------------
-- organization_members / organization_invites
-- -----------------------------------------------------------------------------
alter table public.organization_members enable row level security;

drop policy if exists org_members_select on public.organization_members;
create policy org_members_select on public.organization_members
  for select using (private.is_org_member(organization_id));

drop policy if exists org_members_write_admin on public.organization_members;
create policy org_members_write_admin on public.organization_members
  for all using (private.is_org_admin(organization_id));

alter table public.organization_invites enable row level security;

drop policy if exists org_invites_admin_only on public.organization_invites;
create policy org_invites_admin_only on public.organization_invites
  for all using (private.is_org_admin(organization_id));

-- -----------------------------------------------------------------------------
-- audit_logs — sola lettura per i membri, nessuna scrittura via client
-- (l'unico scrittore legittimo è il backend con la service role, che bypassa la RLS)
-- -----------------------------------------------------------------------------
alter table public.audit_logs enable row level security;

drop policy if exists audit_logs_select_member on public.audit_logs;
create policy audit_logs_select_member on public.audit_logs
  for select using (organization_id is null or private.is_org_member(organization_id));

-- -----------------------------------------------------------------------------
-- assessment_results — lettura per i membri, scrittura per chiunque sia membro
-- (l'assessment lo può eseguire chiunque nel team, non solo l'admin)
-- -----------------------------------------------------------------------------
alter table public.assessment_results enable row level security;

drop policy if exists assessment_results_select on public.assessment_results;
create policy assessment_results_select on public.assessment_results
  for select using (private.is_org_member(organization_id));

drop policy if exists assessment_results_insert on public.assessment_results;
create policy assessment_results_insert on public.assessment_results
  for insert with check (private.is_org_member(organization_id));

-- -----------------------------------------------------------------------------
-- compliance_measures — lettura per i membri, scrittura riservata agli admin
-- (i Viewer hanno accesso in sola lettura, come da ruoli definiti in Fase 1)
-- -----------------------------------------------------------------------------
alter table public.compliance_measures enable row level security;

drop policy if exists compliance_measures_select on public.compliance_measures;
create policy compliance_measures_select on public.compliance_measures
  for select using (private.is_org_member(organization_id));

drop policy if exists compliance_measures_write_admin on public.compliance_measures;
create policy compliance_measures_write_admin on public.compliance_measures
  for all using (private.is_org_admin(organization_id));

-- -----------------------------------------------------------------------------
-- documents
-- -----------------------------------------------------------------------------
alter table public.documents enable row level security;

drop policy if exists documents_select on public.documents;
create policy documents_select on public.documents
  for select using (private.is_org_member(organization_id));

drop policy if exists documents_write_admin on public.documents;
create policy documents_write_admin on public.documents
  for all using (private.is_org_admin(organization_id));

-- -----------------------------------------------------------------------------
-- incidents / incident_notifications
-- -----------------------------------------------------------------------------
alter table public.incidents enable row level security;

drop policy if exists incidents_select on public.incidents;
create policy incidents_select on public.incidents
  for select using (private.is_org_member(organization_id));

drop policy if exists incidents_write on public.incidents;
create policy incidents_write on public.incidents
  for all using (private.is_org_member(organization_id));

alter table public.incident_notifications enable row level security;

drop policy if exists incident_notifications_select on public.incident_notifications;
create policy incident_notifications_select on public.incident_notifications
  for select using (
    exists (
      select 1 from public.incidents i
      where i.id = incident_notifications.incident_id
        and private.is_org_member(i.organization_id)
    )
  );

-- -----------------------------------------------------------------------------
-- suppliers / supplier_questionnaires
-- Nota: il flusso "il fornitore compila il questionario senza account" (Fase 4) passa
-- sempre dal backend con la service role e un access_token dedicato, MAI da una sessione
-- Supabase autenticata: per questo supplier_questionnaires non ha una policy pubblica qui,
-- solo quella per i membri del team che consultano le risposte già raccolte.
-- -----------------------------------------------------------------------------
alter table public.suppliers enable row level security;

drop policy if exists suppliers_select on public.suppliers;
create policy suppliers_select on public.suppliers
  for select using (private.is_org_member(organization_id));

drop policy if exists suppliers_write on public.suppliers;
create policy suppliers_write on public.suppliers
  for all using (private.is_org_member(organization_id));

alter table public.supplier_questionnaires enable row level security;

drop policy if exists supplier_questionnaires_select on public.supplier_questionnaires;
create policy supplier_questionnaires_select on public.supplier_questionnaires
  for select using (
    exists (
      select 1 from public.suppliers s
      where s.id = supplier_questionnaires.supplier_id
        and private.is_org_member(s.organization_id)
    )
  );

-- -----------------------------------------------------------------------------
-- subscriptions — sola lettura per i membri; scrittura solo da backend (service role)
-- -----------------------------------------------------------------------------
alter table public.subscriptions enable row level security;

drop policy if exists subscriptions_select on public.subscriptions;
create policy subscriptions_select on public.subscriptions
  for select using (private.is_org_member(organization_id));
