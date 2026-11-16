from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import lire_jeton
from app.db.session import get_db
from app.models import Utilisateur
from app.services.droits import Droits, calculer_droits

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def utilisateur_courant(jeton: str = Depends(oauth2), db: Session = Depends(get_db)) -> Utilisateur:
    uid = lire_jeton(jeton)
    u = db.get(Utilisateur, uid) if uid else None
    if not u or not u.actif:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée, reconnectez-vous", headers={"WWW-Authenticate": "Bearer"})
    db.info["utilisateur_id"] = u.id  # utilisé par le trigger d'audit (transactions suivantes)
    db.execute(text("SELECT set_config('arenah.utilisateur_id', :u, true)"), {"u": str(u.id)})  # transaction en cours
    return u


def droits_courants(u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)) -> Droits:
    return calculer_droits(db, u)


def exiger_roles(*codes: str):
    """Dépendance : l'utilisateur doit avoir au moins un de ces rôles (ou être superutilisateur)."""
    def verif(d: Droits = Depends(droits_courants)) -> Droits:
        if not d.a_role(*codes):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Vous n'avez pas les droits pour cette action")
        return d
    return verif
