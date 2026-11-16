from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import droits_courants, exiger_roles, utilisateur_courant
from app.core.security import creer_jeton, hacher, mot_de_passe_provisoire, verifier
from app.db.session import get_db
from app.models import Employe, Utilisateur
from app.schemas.divers import ChangementMotDePasse, Jeton, Moi, MotDePasseProvisoire
from app.services.droits import Droits

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton)
def connexion(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    u = db.scalar(select(Utilisateur).where(func.lower(Utilisateur.login) == form.username.strip().lower()))
    if not u or not u.actif or not verifier(form.password, u.mot_de_passe_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect")
    u.derniere_connexion = datetime.now(timezone.utc)
    db.commit()
    return Jeton(access_token=creer_jeton(u.id), doit_changer_mdp=u.doit_changer_mdp)


@router.get("/moi", response_model=Moi)
def moi(u: Utilisateur = Depends(utilisateur_courant), d: Droits = Depends(droits_courants), db: Session = Depends(get_db)):
    e = db.get(Employe, u.employe_id) if u.employe_id else None
    return Moi(
        utilisateur_id=u.id, login=u.login, employe_id=u.employe_id,
        nom_complet=(f"{e.civilite} {e.nom} {e.prenom}".strip() if e else "Administrateur"),
        superutilisateur=u.est_superutilisateur, doit_changer_mdp=u.doit_changer_mdp, langue=u.langue,
        roles=sorted(d.roles), roles_delegues=sorted(d.roles_delegues), postes=d.postes,
        portee_globale=d.unites_portee is None,
        unites_portee=sorted(d.unites_portee) if d.unites_portee is not None else None,
        peut_voir_salaires=d.peut_voir_salaires,
    )


@router.post("/changer-mot-de-passe", status_code=204)
def changer_mot_de_passe(data: ChangementMotDePasse, u: Utilisateur = Depends(utilisateur_courant), db: Session = Depends(get_db)):
    if not verifier(data.ancien, u.mot_de_passe_hash):
        raise HTTPException(400, "Ancien mot de passe incorrect")
    if data.ancien == data.nouveau:
        raise HTTPException(400, "Le nouveau mot de passe doit être différent de l'ancien")
    u.mot_de_passe_hash = hacher(data.nouveau)
    u.doit_changer_mdp = False
    db.commit()


@router.post("/utilisateurs/{utilisateur_id}/mot-de-passe-provisoire", response_model=MotDePasseProvisoire)
def generer_mot_de_passe_provisoire(utilisateur_id: int, db: Session = Depends(get_db),
                                    _: Droits = Depends(exiger_roles("RH", "ASSISTANT_RH", "ADMIN_INFO"))):
    """Décision 34 : le RH ou l'informatique génère un mot de passe provisoire (tracé dans le journal)."""
    u = db.get(Utilisateur, utilisateur_id)
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    mdp = mot_de_passe_provisoire()
    u.mot_de_passe_hash = hacher(mdp)
    u.doit_changer_mdp = True
    db.commit()
    return MotDePasseProvisoire(login=u.login, mot_de_passe_provisoire=mdp)
