"""Employés, affectations (cumul de postes) et délégations. Portée limitée à l'unité pour les rôles non transverses."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import droits_courants, exiger_roles
from app.core.security import hacher
from app.core.config import settings
from app.db.session import get_db
from app.models import Affectation, Delegation, Employe, Poste, Utilisateur
from app.schemas.organisation import (
    AffectationEntree, AffectationSortie, DelegationEntree, DelegationSortie, EmployeEntree, EmployeSortie,
    FinAffectation, SortieEmploye,
)
from app.services.droits import Droits

router = APIRouter(tags=["Employés"])
GESTION_RH = ("RH", "ASSISTANT_RH", "PDG", "DIRECTEUR", "ADMIN_INFO")


def _nom(e: Employe) -> str:
    return f"{e.civilite} {e.nom} {e.prenom}".strip()


def _affs_en_cours(db: Session, employe_ids: list[int] | None = None, jour: date | None = None):
    jour = jour or date.today()
    q = (select(Affectation).options(joinedload(Affectation.poste).joinedload(Poste.unite))
         .where(Affectation.date_debut <= jour, or_(Affectation.date_fin.is_(None), Affectation.date_fin >= jour)))
    if employe_ids is not None:
        q = q.where(Affectation.employe_id.in_(employe_ids))
    return db.scalars(q).all()


def _sortie(e: Employe, affs: list[Affectation], login: str | None) -> EmployeSortie:
    s = EmployeSortie.model_validate(e)
    s.postes = [f"{a.poste.intitule} – {a.poste.unite.nom}" for a in affs]
    s.unites = sorted({a.poste.unite.nom for a in affs})
    s.login = login
    return s


def _verifier_portee(db: Session, d: Droits, employe_id: int):
    if d.unites_portee is None:
        return
    unites = {a.poste.unite_id for a in _affs_en_cours(db, [employe_id])}
    if employe_id != d.employe_id and not (unites & d.unites_portee):
        raise HTTPException(403, "Cet employé n'est pas dans votre périmètre")


# ---------------------------------------------------------- Employés
@router.get("/employes", response_model=list[EmployeSortie])
def lister_employes(recherche: str | None = None, statut: str | None = None, unite_id: int | None = None,
                    db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    q = select(Employe).order_by(Employe.nom, Employe.prenom)
    if statut:
        q = q.where(Employe.statut == statut)
    if recherche:
        motif = f"%{recherche.strip()}%"
        q = q.where(or_(Employe.nom.ilike(motif), Employe.prenom.ilike(motif), Employe.matricule.ilike(motif)))
    employes = db.scalars(q).all()
    affs = _affs_en_cours(db, [e.id for e in employes])
    par_emp: dict[int, list[Affectation]] = {}
    for a in affs:
        par_emp.setdefault(a.employe_id, []).append(a)
    logins = dict(db.execute(select(Utilisateur.employe_id, Utilisateur.login).where(Utilisateur.employe_id.is_not(None))).all())
    res = []
    for e in employes:
        ea = par_emp.get(e.id, [])
        unites = {a.poste.unite_id for a in ea}
        if d.unites_portee is not None and e.id != d.employe_id and not (unites & d.unites_portee):
            continue
        if unite_id and unite_id not in unites:
            continue
        res.append(_sortie(e, ea, logins.get(e.id)))
    return res


@router.get("/employes/{employe_id}", response_model=EmployeSortie)
def lire_employe(employe_id: int, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    e = db.get(Employe, employe_id)
    if not e:
        raise HTTPException(404, "Employé introuvable")
    _verifier_portee(db, d, employe_id)
    login = db.scalar(select(Utilisateur.login).where(Utilisateur.employe_id == employe_id))
    return _sortie(e, _affs_en_cours(db, [employe_id]), login)


@router.post("/employes", response_model=EmployeSortie, status_code=201)
def creer_employe(data: EmployeEntree, creer_compte: bool = True, db: Session = Depends(get_db),
                  _: Droits = Depends(exiger_roles(*GESTION_RH))):
    if db.scalar(select(Employe.id).where(Employe.matricule == data.matricule)):
        raise HTTPException(400, "Ce matricule existe déjà")
    e = Employe(**data.model_dump())
    db.add(e)
    db.flush()
    login = None
    if creer_compte:
        base = "".join(c for c in (data.prenom or data.nom).lower() if c.isalnum()) or data.matricule.lower()
        login, i = base, 1
        while db.scalar(select(Utilisateur.id).where(Utilisateur.login == login)):
            i += 1
            login = f"{base}{i}"
        db.add(Utilisateur(employe_id=e.id, login=login, mot_de_passe_hash=hacher(settings.mot_de_passe_provisoire), doit_changer_mdp=True))
    db.commit()
    return _sortie(e, [], login)


@router.put("/employes/{employe_id}", response_model=EmployeSortie)
def modifier_employe(employe_id: int, data: EmployeEntree, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*GESTION_RH))):
    e = db.get(Employe, employe_id)
    if not e:
        raise HTTPException(404, "Employé introuvable")
    _verifier_portee(db, d, employe_id)
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    db.commit()
    login = db.scalar(select(Utilisateur.login).where(Utilisateur.employe_id == employe_id))
    return _sortie(e, _affs_en_cours(db, [employe_id]), login)


@router.post("/employes/{employe_id}/sortie", response_model=EmployeSortie)
def enregistrer_sortie(employe_id: int, data: SortieEmploye, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_RH))):
    """Sortie de l'employé : affectations terminées, compte désactivé (pas de suppression)."""
    e = db.get(Employe, employe_id)
    if not e:
        raise HTTPException(404, "Employé introuvable")
    e.statut, e.date_sortie, e.motif_sortie = "sorti", data.date_sortie, data.motif_sortie
    for a in _affs_en_cours(db, [employe_id]):
        a.date_fin = data.date_sortie
    u = db.scalar(select(Utilisateur).where(Utilisateur.employe_id == employe_id))
    if u:
        u.actif = False
    db.commit()
    return _sortie(e, [], u.login if u else None)


# ---------------------------------------------------------- Affectations
def _aff_sortie(a: Affectation) -> AffectationSortie:
    s = AffectationSortie.model_validate(a)
    s.employe_nom = _nom(a.employe)
    s.poste_libelle = f"{a.poste.intitule} – {a.poste.unite.nom}"
    s.en_cours = a.date_fin is None or a.date_fin >= date.today()
    return s


@router.get("/affectations", response_model=list[AffectationSortie])
def lister_affectations(employe_id: int | None = None, en_cours: bool = False, db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    q = select(Affectation).options(joinedload(Affectation.employe), joinedload(Affectation.poste).joinedload(Poste.unite)).order_by(Affectation.date_debut.desc())
    if employe_id:
        q = q.where(Affectation.employe_id == employe_id)
    if en_cours:
        q = q.where(or_(Affectation.date_fin.is_(None), Affectation.date_fin >= date.today()))
    return [_aff_sortie(a) for a in db.scalars(q).all()]


@router.post("/affectations", response_model=AffectationSortie, status_code=201)
def creer_affectation(data: AffectationEntree, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_RH))):
    if not db.get(Employe, data.employe_id) or not db.get(Poste, data.poste_id):
        raise HTTPException(400, "Employé ou poste introuvable")
    if data.date_fin and data.date_fin < data.date_debut:
        raise HTTPException(400, "La date de fin précède la date de début")
    a = Affectation(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _aff_sortie(a)


@router.put("/affectations/{affectation_id}/terminer", response_model=AffectationSortie)
def terminer_affectation(affectation_id: int, data: FinAffectation, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_RH))):
    """Un transfert de poste = fin de l'ancienne affectation + nouvelle affectation : les droits suivent."""
    a = db.get(Affectation, affectation_id)
    if not a:
        raise HTTPException(404, "Affectation introuvable")
    if data.date_fin < a.date_debut:
        raise HTTPException(400, "La date de fin précède la date de début")
    a.date_fin = data.date_fin
    if data.motif:
        a.motif = data.motif
    db.commit()
    return _aff_sortie(a)


# ---------------------------------------------------------- Délégations
def _del_sortie(dl: Delegation) -> DelegationSortie:
    s = DelegationSortie.model_validate(dl)
    s.delegant_nom, s.delegataire_nom = _nom(dl.delegant), _nom(dl.delegataire)
    s.poste_libelle = f"{dl.poste.intitule} – {dl.poste.unite.nom}"
    return s


@router.get("/delegations", response_model=list[DelegationSortie])
def lister_delegations(actives: bool = False, db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    q = select(Delegation).options(joinedload(Delegation.delegant), joinedload(Delegation.delegataire),
                                   joinedload(Delegation.poste).joinedload(Poste.unite)).order_by(Delegation.date_debut.desc())
    if actives:
        q = q.where(Delegation.date_debut <= date.today(), Delegation.date_fin >= date.today())
    return [_del_sortie(x) for x in db.scalars(q).all()]


@router.post("/delegations", response_model=DelegationSortie, status_code=201)
def creer_delegation(data: DelegationEntree, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    """Le titulaire du poste (ou RH / direction) délègue son poste pour une période (remplacement)."""
    titulaire = db.scalar(select(Affectation.id).where(Affectation.employe_id == data.delegant_id, Affectation.poste_id == data.poste_id,
                                                       or_(Affectation.date_fin.is_(None), Affectation.date_fin >= data.date_debut)))
    if not titulaire:
        raise HTTPException(400, "Le délégant n'occupe pas ce poste")
    if not (d.employe_id == data.delegant_id or d.a_role(*GESTION_RH)):
        raise HTTPException(403, "Seul le titulaire, le RH ou la direction peut créer cette délégation")
    if data.delegant_id == data.delegataire_id or data.date_fin < data.date_debut:
        raise HTTPException(400, "Délégation incohérente")
    dl = Delegation(**data.model_dump())
    db.add(dl)
    db.commit()
    db.refresh(dl)
    return _del_sortie(dl)


@router.put("/delegations/{delegation_id}/terminer", response_model=DelegationSortie)
def terminer_delegation(delegation_id: int, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    dl = db.get(Delegation, delegation_id)
    if not dl:
        raise HTTPException(404, "Délégation introuvable")
    if not (d.employe_id == dl.delegant_id or d.a_role(*GESTION_RH)):
        raise HTTPException(403, "Action non autorisée")
    dl.date_fin = min(dl.date_fin, date.today())
    db.commit()
    return _del_sortie(dl)
