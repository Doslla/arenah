"""Unités, rôles, postes et organigramme automatique (généré à partir des affectations en cours)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import droits_courants, exiger_roles
from app.db.session import get_db
from app.models import Affectation, Poste, Role, Unite
from app.schemas.organisation import PosteEntree, PosteSortie, RoleSortie, UniteEntree, UniteSortie
from app.services.droits import Droits

router = APIRouter(tags=["Organisation"])
GESTION_ORGA = ("PDG", "DIRECTEUR", "RH", "ADMIN_INFO")


def titulaires_en_cours(db: Session, jour: date | None = None) -> dict[int, list[dict]]:
    jour = jour or date.today()
    affs = db.scalars(select(Affectation).options(joinedload(Affectation.employe))
                      .where(Affectation.date_debut <= jour, or_(Affectation.date_fin.is_(None), Affectation.date_fin >= jour))).all()
    res: dict[int, list[dict]] = {}
    for a in affs:
        e = a.employe
        res.setdefault(a.poste_id, []).append({"employe_id": e.id, "nom": f"{e.civilite} {e.nom} {e.prenom}".strip(), "interim": a.est_interim})
    return res


# ---------------------------------------------------------- Unités
@router.get("/unites", response_model=list[UniteSortie])
def lister_unites(actif: bool | None = None, db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    q = select(Unite).order_by(Unite.ordre_affichage, Unite.id)
    if actif is not None:
        q = q.where(Unite.actif == actif)
    return db.scalars(q).all()


@router.post("/unites", response_model=UniteSortie, status_code=201)
def creer_unite(data: UniteEntree, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_ORGA))):
    if data.parent_id and not db.get(Unite, data.parent_id):
        raise HTTPException(400, "Unité parente introuvable")
    u = Unite(**data.model_dump())
    db.add(u)
    db.commit()
    return u


@router.put("/unites/{unite_id}", response_model=UniteSortie)
def modifier_unite(unite_id: int, data: UniteEntree, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_ORGA))):
    u = db.get(Unite, unite_id)
    if not u:
        raise HTTPException(404, "Unité introuvable")
    if data.parent_id == unite_id:
        raise HTTPException(400, "Une unité ne peut pas être sa propre parente")
    for k, v in data.model_dump().items():
        setattr(u, k, v)
    db.commit()
    return u


@router.delete("/unites/{unite_id}", status_code=204)
def desactiver_unite(unite_id: int, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_ORGA))):
    """Pas de suppression physique : l'unité est désactivée (historique conservé)."""
    u = db.get(Unite, unite_id)
    if not u:
        raise HTTPException(404, "Unité introuvable")
    u.actif = False
    db.commit()


@router.get("/organigramme")
def organigramme(db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    """Arbre des unités actives avec leurs postes et titulaires actuels (décision 9 : les groupes servent aux regroupements)."""
    unites = db.scalars(select(Unite).where(Unite.actif).order_by(Unite.ordre_affichage, Unite.id)).all()
    postes = db.scalars(select(Poste).options(joinedload(Poste.role)).where(Poste.actif).order_by(Poste.est_responsable.desc(), Poste.id)).all()
    tit = titulaires_en_cours(db)
    par_unite: dict[int, list[dict]] = {}
    for p in postes:
        par_unite.setdefault(p.unite_id, []).append({
            "poste_id": p.id, "intitule": p.intitule, "role": p.role.code, "est_responsable": p.est_responsable,
            "titulaires": tit.get(p.id, []), "vacant": not tit.get(p.id),
        })
    noeuds = {u.id: {"id": u.id, "nom": u.nom, "type": u.type, "encaisse": u.encaisse, "postes": par_unite.get(u.id, []), "enfants": []} for u in unites}
    racines = []
    for u in unites:
        if u.parent_id and u.parent_id in noeuds:
            noeuds[u.parent_id]["enfants"].append(noeuds[u.id])
        else:
            racines.append(noeuds[u.id])
    for n in noeuds.values():
        resp = next((p for p in n["postes"] if p["est_responsable"] and p["titulaires"]), None)
        n["responsable"] = resp["titulaires"][0]["nom"] if resp else None
    return racines


# ---------------------------------------------------------- Rôles et postes
@router.get("/roles", response_model=list[RoleSortie])
def lister_roles(db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    return db.scalars(select(Role).order_by(Role.id)).all()


def _poste_sortie(p: Poste, tit: dict) -> PosteSortie:
    s = PosteSortie.model_validate(p)
    s.unite_nom, s.role_code = p.unite.nom, p.role.code
    s.titulaires = [t["nom"] for t in tit.get(p.id, [])]
    return s


@router.get("/postes", response_model=list[PosteSortie])
def lister_postes(unite_id: int | None = None, db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    q = select(Poste).options(joinedload(Poste.unite), joinedload(Poste.role)).order_by(Poste.unite_id, Poste.est_responsable.desc(), Poste.id)
    if unite_id:
        q = q.where(Poste.unite_id == unite_id)
    tit = titulaires_en_cours(db)
    return [_poste_sortie(p, tit) for p in db.scalars(q).all()]


@router.post("/postes", response_model=PosteSortie, status_code=201)
def creer_poste(data: PosteEntree, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_ORGA))):
    p = Poste(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _poste_sortie(p, {})


@router.put("/postes/{poste_id}", response_model=PosteSortie)
def modifier_poste(poste_id: int, data: PosteEntree, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_ORGA))):
    p = db.get(Poste, poste_id)
    if not p:
        raise HTTPException(404, "Poste introuvable")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return _poste_sortie(p, titulaires_en_cours(db))
