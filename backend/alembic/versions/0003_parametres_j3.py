"""paramètres ajoutés au J3

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO parametre (cle, valeur, type, description, modifiable_par)
        SELECT 'heure_debut_defaut', '08:00', 'texte', 'Heure d''arrivée prévue par défaut (sans planning)', 'RH,PDG'
        WHERE NOT EXISTS (SELECT 1 FROM parametre WHERE cle = 'heure_debut_defaut')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM parametre WHERE cle = 'heure_debut_defaut'")
