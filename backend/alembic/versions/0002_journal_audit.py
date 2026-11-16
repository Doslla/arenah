"""journal d'audit par trigger PostgreSQL (non modifiable)

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

FONCTION = """
CREATE OR REPLACE FUNCTION arenah_audit() RETURNS trigger AS $$
DECLARE
    uid integer := NULLIF(current_setting('arenah.utilisateur_id', true), '')::integer;
BEGIN
    -- L'import de l'historique n'est pas journalisé ligne par ligne
    IF current_setting('arenah.import', true) = 'oui' THEN
        RETURN COALESCE(NEW, OLD);
    END IF;
    IF TG_OP = 'INSERT' THEN
        INSERT INTO journal_audit (utilisateur_id, action, table_nom, entite_id, valeurs_apres)
        VALUES (uid, TG_OP, TG_TABLE_NAME, to_jsonb(NEW)->>'id', to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO journal_audit (utilisateur_id, action, table_nom, entite_id, valeurs_avant, valeurs_apres)
        VALUES (uid, TG_OP, TG_TABLE_NAME, to_jsonb(NEW)->>'id', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSE
        INSERT INTO journal_audit (utilisateur_id, action, table_nom, entite_id, valeurs_avant)
        VALUES (uid, TG_OP, TG_TABLE_NAME, to_jsonb(OLD)->>'id', to_jsonb(OLD));
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION arenah_journal_protege() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Le journal d''audit ne peut être ni modifié ni supprimé';
END;
$$ LANGUAGE plpgsql;
"""

POSER_TRIGGERS = """
DO $$
DECLARE t text;
BEGIN
    FOR t IN SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
               AND table_name NOT IN ('journal_audit', 'alembic_version')
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_audit ON %I', t);
        EXECUTE format('CREATE TRIGGER trg_audit AFTER INSERT OR UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION arenah_audit()', t);
    END LOOP;
END $$;

CREATE TRIGGER trg_journal_protege BEFORE UPDATE OR DELETE ON journal_audit
    FOR EACH ROW EXECUTE FUNCTION arenah_journal_protege();
CREATE TRIGGER trg_journal_protege_truncate BEFORE TRUNCATE ON journal_audit
    FOR EACH STATEMENT EXECUTE FUNCTION arenah_journal_protege();
"""

RETIRER_TRIGGERS = """
DO $$
DECLARE t text;
BEGIN
    FOR t IN SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_audit ON %I', t);
    END LOOP;
END $$;
DROP TRIGGER IF EXISTS trg_journal_protege ON journal_audit;
DROP TRIGGER IF EXISTS trg_journal_protege_truncate ON journal_audit;
DROP FUNCTION IF EXISTS arenah_audit();
DROP FUNCTION IF EXISTS arenah_journal_protege();
"""


def upgrade() -> None:
    op.execute(FONCTION)
    op.execute(POSER_TRIGGERS)


def downgrade() -> None:
    op.execute(RETIRER_TRIGGERS)
