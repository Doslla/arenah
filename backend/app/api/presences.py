"""Présences par badge QR (décisions 14, 15, 16) et avertissements proposés au RH."""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.core.deps import droits_courants, exiger_roles
from app.db.session import get_db
from app.models import Avertissement, Employe, Presence, Unite
from app.services.circuits import notifier_role, parametre, unite_principale
from app.services.droits import Droits

router = APIRouter(tags=["Présences"])
POINTEURS = ("RESPONSABLE_ACTIVITE", "DIRECTEUR", "RH", "ASSISTANT_RH", "PDG", "ADMIN_INFO")


class Scan(BaseModel):
    qr_token: str = Field(min_length=8)


class SaisieManuelle(BaseModel):
    employe_id: int
    date: date
    statut: str = Field(pattern="^(présent|retard|absent)$")
    heure_arrivee: time | None = None
    heure_depart: time | None = None
    motif: str | None = None


class Justification(BaseModel):
    justifiee: bool


class DecisionAvertissement(BaseModel):
    statut: str = Field(pattern="^(émis|annulé)$")
    motif: str | None = None


def _nom(e: Employe) -> str:
    return f"{e.civilite} {e.nom} {e.prenom}".strip()


def _heure_prevue(db: Session) -> time:
    return datetime.strptime(parametre(db, "heure_debut_defaut", "08:00"), "%H:%M").time()


def _sortie(p: Presence, e: Employe, unite: str) -> dict:
    return {"id": str(p.id), "date": str(p.date), "employe_id": e.id, "employe": _nom(e), "unite_id": p.unite_id, "unite": unite,
            "heure_prevue": p.heure_prevue.strftime("%H:%M") if p.heure_prevue else None,
            "heure_arrivee": p.heure_arrivee.strftime("%H:%M") if p.heure_arrivee else None,
            "heure_depart": p.heure_depart.strftime("%H:%M") if p.heure_depart else None,
            "statut": p.statut, "absence_justifiee": p.absence_justifiee, "source_saisie": p.source_saisie}


@router.get("/presences")
def lister_presences(jour: date | None = None, du: date | None = None, au: date | None = None, unite_id: int | None = None,
                     employe_id: int | None = None, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    du, au = (du or jour or date.today()), (au or jour or date.today())
    q = (select(Presence, Employe, Unite.nom).join(Employe, Employe.id == Presence.employe_id).join(Unite, Unite.id == Presence.unite_id)
         .where(Presence.date.between(du, au)).order_by(Presence.date.desc(), Employe.nom))
    if unite_id:
        q = q.where(Presence.unite_id == unite_id)
    if employe_id:
        q = q.where(Presence.employe_id == employe_id)
    res = []
    for p, e, un in db.execute(q).all():
        if d.voit_unite(p.unite_id) or e.id == d.employe_id:
            res.append(_sortie(p, e, un))
    return res


@router.post("/presences/scan")
def scanner(data: Scan, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*POINTEURS))):
    """1er scan du jour = arrivée (retard si au-delà de la tolérance), 2e scan = départ."""
    e = db.scalar(select(Employe).where(Employe.qr_token == data.qr_token.strip()))
    if not e or e.statut != "actif":
        raise HTTPException(404, "Badge inconnu ou employé sorti")
    unite_id = unite_principale(db, e.id)
    if unite_id is None or not d.voit_unite(unite_id):
        raise HTTPException(403, f"{_nom(e)} ne fait pas partie de votre équipe")
    maintenant = datetime.now().replace(second=0, microsecond=0)
    p = db.scalar(select(Presence).where(Presence.employe_id == e.id, Presence.date == maintenant.date()))
    if p and p.heure_arrivee and not p.heure_depart:
        p.heure_depart = maintenant
        action = "départ"
    elif p and p.heure_depart:
        raise HTTPException(400, f"Arrivée et départ déjà enregistrés aujourd'hui pour {_nom(e)}")
    else:
        prevue = _heure_prevue(db)
        tolerance = int(parametre(db, "tolerance_retard_min", "10"))
        retard = maintenant > datetime.combine(maintenant.date(), prevue) + timedelta(minutes=tolerance)
        if p is None:
            p = Presence(employe_id=e.id, unite_id=unite_id, date=maintenant.date())
            db.add(p)
        p.heure_prevue, p.heure_arrivee, p.statut = prevue, maintenant, ("retard" if retard else "présent")
        p.source_saisie, p.saisi_par, p.absence_justifiee = "QR", d.employe_id, None
        action = "arrivée en retard" if retard else "arrivée"
    db.commit()
    return {"employe": _nom(e), "action": action, "heure": maintenant.strftime("%H:%M"), "statut": p.statut}


@router.post("/presences/manuel")
def saisie_manuelle(data: SaisieManuelle, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*POINTEURS))):
    """Saisie de secours si le responsable est absent ou le badge illisible (décision 14)."""
    e = db.get(Employe, data.employe_id)
    if not e:
        raise HTTPException(404, "Employé introuvable")
    unite_id = unite_principale(db, e.id)
    if unite_id is None or not d.voit_unite(unite_id):
        raise HTTPException(403, "Employé hors de votre périmètre")
    p = db.scalar(select(Presence).where(Presence.employe_id == e.id, Presence.date == data.date))
    if p is None:
        p = Presence(employe_id=e.id, unite_id=unite_id, date=data.date)
        db.add(p)
    p.statut, p.source_saisie, p.saisi_par, p.heure_prevue = data.statut, "manuel", d.employe_id, _heure_prevue(db)
    p.heure_arrivee = datetime.combine(data.date, data.heure_arrivee) if data.heure_arrivee and data.statut != "absent" else None
    p.heure_depart = datetime.combine(data.date, data.heure_depart) if data.heure_depart and data.statut != "absent" else None
    p.absence_justifiee = False if data.statut == "absent" else None
    db.commit()
    return _sortie(p, e, db.get(Unite, unite_id).nom)


@router.put("/presences/{presence_id}/justifier")
def justifier(presence_id: str, data: Justification, db: Session = Depends(get_db), _: Droits = Depends(exiger_roles("RH", "ASSISTANT_RH", "RESPONSABLE_ACTIVITE", "DIRECTEUR"))):
    p = db.get(Presence, presence_id)
    if not p or p.statut != "absent":
        raise HTTPException(404, "Absence introuvable")
    p.absence_justifiee = data.justifiee
    db.commit()
    return {"id": presence_id, "absence_justifiee": p.absence_justifiee}


def proposer_avertissements(db: Session, jour: date | None = None) -> int:
    """Absences non justifiées après le délai : rappel à l'ordre proposé dès la 1re, avertissement à la Ne du mois (le RH décide)."""
    jour = jour or date.today()
    delai = int(parametre(db, "delai_justificatif_heures", "48"))
    seuil = int(parametre(db, "absences_avant_avertissement", "3"))
    limite = jour - timedelta(days=max(1, delai // 24))
    absences = db.scalars(select(Presence).where(Presence.statut == "absent", Presence.absence_justifiee.is_not(True),
                                                 Presence.date <= limite, Presence.date >= limite - timedelta(days=31))
                          .order_by(Presence.employe_id, Presence.date)).all()
    deja = {(a.employe_id, a.motif) for a in db.scalars(select(Avertissement).where(Avertissement.origine == "absence injustifiée"))}
    crees = 0
    for p in absences:
        rang = db.scalar(select(func.count(Presence.id)).where(
            Presence.employe_id == p.employe_id, Presence.statut == "absent", Presence.absence_justifiee.is_not(True),
            extract("month", Presence.date) == p.date.month, extract("year", Presence.date) == p.date.year, Presence.date <= p.date))
        type_ = "avertissement" if rang >= seuil else ("rappel à l'ordre" if rang == 1 else None)
        if not type_:
            continue
        motif = f"Absence non justifiée du {p.date.strftime('%d/%m/%Y')} ({rang}e du mois)"
        if (p.employe_id, motif) in deja:
            continue
        db.add(Avertissement(employe_id=p.employe_id, type=type_, motif=motif, origine="absence injustifiée", statut="proposé", date=jour))
        crees += 1
    if crees:
        notifier_role(db, ["RH"], f"{crees} avertissement(s) proposé(s) pour absence non justifiée", "/presences")
    db.commit()
    return crees


@router.get("/avertissements")
def lister_avertissements(statut: str | None = None, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    q = select(Avertissement, Employe).join(Employe, Employe.id == Avertissement.employe_id).order_by(Avertissement.date.desc())
    if statut:
        q = q.where(Avertissement.statut == statut)
    if not d.a_role("RH", "ASSISTANT_RH", "PDG", "DIRECTEUR"):
        q = q.where(Avertissement.employe_id == d.employe_id)  # chacun voit les siens
    return [{"id": a.id, "employe_id": e.id, "employe": _nom(e), "type": a.type, "motif": a.motif, "origine": a.origine,
             "statut": a.statut, "date": str(a.date), "lu_par_employe": a.lu_par_employe} for a, e in db.execute(q).all()]


@router.put("/avertissements/{avertissement_id}")
def decider_avertissement(avertissement_id: int, data: DecisionAvertissement, db: Session = Depends(get_db),
                          d: Droits = Depends(exiger_roles("RH", "ASSISTANT_RH"))):
    """Le système propose, le RH décide (décision 16). Sans effet sur la paie (décision 2)."""
    a = db.get(Avertissement, avertissement_id)
    if not a:
        raise HTTPException(404, "Avertissement introuvable")
    a.statut, a.emis_par = data.statut, d.employe_id
    if data.motif:
        a.motif = f"{a.motif} — {data.motif}"
    db.commit()
    return {"id": a.id, "statut": a.statut}


@router.get("/badges")
def badges(db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    """Badges QR à imprimer : ceux du périmètre pour les responsables, le sien pour les autres."""
    res = []
    for e in db.scalars(select(Employe).where(Employe.statut == "actif").order_by(Employe.nom)):
        u = unite_principale(db, e.id)
        if e.id == d.employe_id or (d.a_role(*POINTEURS) and u is not None and d.voit_unite(u)):
            res.append({"employe_id": e.id, "nom": _nom(e), "matricule": e.matricule, "unite": db.get(Unite, u).nom if u else "",
                        "qr_token": e.qr_token})
    return res
