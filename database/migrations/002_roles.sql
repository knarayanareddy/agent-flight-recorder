-- PostgreSQL roles without passwords. Operator provisions login/service identities externally.
BEGIN;
DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='baseline_app') THEN CREATE ROLE baseline_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; END IF;
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='baseline_lifecycle') THEN CREATE ROLE baseline_lifecycle NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; END IF;
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='baseline_dispatcher') THEN CREATE ROLE baseline_dispatcher NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; END IF;
END $$;
GRANT USAGE ON SCHEMA core,afr,skb,evf TO baseline_app,baseline_lifecycle,baseline_dispatcher;
GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA core,afr,skb,evf TO baseline_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA core,afr,skb,evf TO baseline_app;
REVOKE ALL ON skb.hidden_answers FROM baseline_app;
REVOKE INSERT,UPDATE,DELETE ON core.organizations,core.users,core.memberships,core.project_roles,core.api_keys FROM baseline_app;
REVOKE UPDATE,DELETE ON core.audit_events,afr.events,afr.cases,skb.analyses,evf.reviews,skb.package_reviews FROM baseline_app;
GRANT SELECT,DELETE ON ALL TABLES IN SCHEMA core,afr,skb,evf TO baseline_lifecycle;
REVOKE DELETE ON core.audit_events FROM baseline_lifecycle;
GRANT SELECT,UPDATE ON core.jobs,core.job_attempts,core.outbox,core.budget_reservations TO baseline_dispatcher;
GRANT INSERT ON core.job_attempts TO baseline_dispatcher;
-- Every project-bearing table has a policy; the trusted API sets context locally only AFTER auth checks.
DO $$ DECLARE rec record; expr text; BEGIN
 FOR rec IN SELECT table_schema,table_name FROM information_schema.columns
  WHERE table_schema IN ('core','afr','skb','evf') AND column_name='project_id' LOOP
  expr := 'project_id = nullif(current_setting(''baseline.project_id'', true), '''')::uuid';
  EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',rec.table_schema,rec.table_name);
  EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY',rec.table_schema,rec.table_name);
  EXECUTE format('CREATE POLICY project_scope ON %I.%I USING (%s) WITH CHECK (%s)',rec.table_schema,rec.table_name,expr,expr);
 END LOOP;
END $$;
ALTER TABLE core.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.projects FORCE ROW LEVEL SECURITY;
CREATE POLICY projects_org_scope ON core.projects USING (organization_id=nullif(current_setting('baseline.organization_id',true),'')::uuid) WITH CHECK (organization_id=nullif(current_setting('baseline.organization_id',true),'')::uuid);
-- The application must set project/organization context transaction-locally; pooled context MUST NOT persist.
-- RLS is defense in depth against query bugs, NOT authorization against a compromised trusted application.
-- Dispatcher iterates authorized project scopes supplied by the trusted scheduler; no global BYPASSRLS worker.
COMMIT;
