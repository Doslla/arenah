"""Paramètres (valeurs réglables sans toucher au code), calendrier et référentiels."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import droits_courants, exiger_roles
from app.db.session import get_db
from app.models import CategorieDepense, CategorieRecette, EvenementCalendrier, Parametre, TypeAbsence, TypeContrat
from app.schemas.divers import EvenementEntree, EvenementSortie, ParametreMaj, ParametreSortie, Referentiel
from app.services.droits import Droits

router = APIRouter(tags=["Paramètres"])


@router.get("/parametres", response_model=list[ParametreSortie])
def lister_parametres(db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    return db.scalars(select(Parametre).order_by(Parametre.cle)).all()


@router.put("/parametres/{cle}", response_model=ParametreSortie)
def modifier_parametre(cle: str, data: ParametreMaj, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    p = db.scalar(select(Parametre).where(Parametre.cle == cle))
    if not p:
        raise HTTPException(404, "Paramètre inconnu")
    autorises = [r.strip() for r in p.modifiable_par.split(",") if r.strip()]
    if not d.a_role(*autorises):
        raise HTTPException(403, f"Paramètre modifiable par : {', '.join(autorises)}")
    try:  # contrôle du type
        if p.type == "entier":
            int(data.valeur)
        elif p.type == "decimal":
            float(data.valeur.replace(",", "."))
        elif p.type == "booleen" and data.valeur not in ("oui", "non"):
            raise ValueError
    except ValueError:
        raise HTTPException(400, f"Valeur invalide pour un paramètre de type {p.type}")
    p.valeur = data.valeur
    db.commit()
    return p


# ---------------------------------------------------------- Calendrier
GESTION_CAL = ("RH", "ASSISTANT_RH", "PDG", "ADMIN_INFO")


@router.get("/calendrier", response_model=list[EvenementSortie])
def lister_calendrier(type: str | None = None, annee: int | None = None, db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    q = select(EvenementCalendrier).order_by(EvenementCalendrier.date_debut)
    if type:
        q = q.where(EvenementCalendrier.type == type)
    evts = db.scalars(q).all()
    if annee:
        evts = [e for e in evts if e.date_debut.year == annee or e.date_fin.year == annee]
    return evts


@router.post("/calendrier", response_model=EvenementSortie, status_code=201)
def creer_evenement(data: EvenementEntree, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_CAL))):
    if data.date_fin < data.date_debut:
        raise HTTPException(400, "La date de fin précède la date de début")
    e = EvenementCalendrier(**data.model_dump())
    db.add(e)
    db.commit()
    return e


@router.put("/calendrier/{evenement_id}", response_model=EvenementSortie)
def modifier_evenement(evenement_id: int, data: EvenementEntree, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_CAL))):
    e = db.get(EvenementCalendrier, evenement_id)
    if not e:
        raise HTTPException(404, "Événement introuvable")
    for k, v in data.model_dump().items():
        setattr(e, k, v)
    db.commit()
    return e


@router.delete("/calendrier/{evenement_id}", status_code=204)
def supprimer_evenement(evenement_id: int, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles(*GESTION_CAL))):
    e = db.get(EvenementCalendrier, evenement_id)
    if not e:
        raise HTTPException(404, "Événement introuvable")
    if e.type == "ferie":
        raise HTTPException(400, "Un jour férié ne se supprime pas : modifiez-le (décision 20)")
    db.delete(e)
    db.commit()


# ---------------------------------------------------------- Référentiels
@router.get("/referentiels/{nom}", response_model=list[Referentiel])
def lister_referentiel(nom: str, db: Session = Depends(get_db), _: Droits = Depends(droits_courants)):
    modeles = {"types-contrat": TypeContrat, "types-absence": TypeAbsence, "categories-recette": CategorieRecette, "categories-depense": CategorieDepense}
    if nom not in modeles:
        raise HTTPException(404, f"Référentiels disponibles : {', '.join(modeles)}")
    m = modeles[nom]
    return db.scalars(select(m).order_by(m.libelle)).all()
