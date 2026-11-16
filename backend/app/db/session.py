from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True,
                       connect_args={"options": f"-c timezone={settings.fuseau_horaire}"})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _poser_contexte_audit(session, transaction, connection):
    """Transmet l'utilisateur connecté au trigger d'audit PostgreSQL (journal non modifiable)."""
    uid = session.info.get("utilisateur_id")
    if uid is not None:
        connection.execute(text("SELECT set_config('arenah.utilisateur_id', :u, true)"), {"u": str(uid)})
    if session.info.get("import"):
        connection.execute(text("SELECT set_config('arenah.import', 'oui', true)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
