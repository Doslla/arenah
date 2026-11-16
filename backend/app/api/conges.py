"""Congés (décisions 1, 17, 18, 39) : employé → responsable (avis) → RH (décision)."""
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.core.deps import droits_courants
from app.db.session import get_db
from app.models import Conge, Employe, ParametreConge, TypeAbsence
from app.services.circuits import noms, notifier, responsable_unite, titulaires_role, unite_principale
from app.services.droits import Droits

router = APIRouter(tags=["Congés"])
GESTION = ("RH", "ASSISTANT_RH", "PDG")


class DemandeConge(BaseModel):
    employe_id: int | None = None  # vide = pour soi-même
    type_absence_id: int
    date_debut: date
    date_fin: date
    motif: str | None = None


class Avis(BaseModel):
    avis: str = Field(pattern="^(favorable|défavorable)$")
    motif: str | None = None


class Decision(BaseModel):
    decision: str = Field(pattern="^(accepté|refusé)$")
    motif: str | None = None


def _nom(e: Employe) -> str:
    return f"{e.civilite} {e.nom} {e.prenom}".strip()


def solde(db: Session, employe_id: int, annee: int | None = None) -> dict:
    """Acquis = jours par mois × mois travaillés dans l'année ; pris = congés décomptés acceptés (report : paramètre)."""
    annee = annee or date.today().year
    e = db.get(Employe, employe_id)
    pc = db.scalar(select(ParametreConge)) or ParametreConge()
    debut = max(e.date_embauche, date(annee, 1, 1))
    fin = min(date.today(), date(annee, 12, 31))
    mois = max(0, (fin.year - debut.year) * 12 + fin.month - debut.month + (1 if fin.day >= debut.day else 0)) if fin >= debut else 0
    acquis = float(pc.jours_acquis_par_mois) * mois
    decompte = select(TypeAbsence.id).where(TypeAbsence.decompte_solde)
    pris = db.scalar(select(func.coalesce(func.sum(Conge.nb_jours), 0)).where(
        Conge.employe_id == employe_id, Conge.statut == "accepté", Conge.type_absence_id.in_(decompte),
        extract("year", Conge.date_debut) == annee)) or 0
    prises = db.scalar(select(func.count(Conge.id)).where(
        Conge.employe_id == employe_id, Conge.statut.in_(("accepté", "en attente avis", "en attente RH")),
        Conge.type_absence_id.in_(decompte), extract("year", Conge.date_debut) == annee))
    anciennete = (date.today().year - e.date_embauche.year) * 12 + date.today().month - e.date_embauche.month
    return {"employe_id": employe_id, "annee": annee, "acquis": round(acquis, 1), "pris": float(pris), "solde": round(acquis - float(pris), 1),
            "prises_annuelles": prises, "prises_max": pc.prises_annuelles_max, "plafond_par_prise": pc.plafond_par_prise,
            "anciennete_mois": anciennete, "anciennete_min_mois": pc.anciennete_min_mois}


def donneurs_avis(db: Session, c: Conge) -> tuple[set[int], bool]:
    """Responsable de l'unité de l'employé ; s'il est lui-même responsable, le supérieur prend la place (décision 39)."""
    u = unite_principale(db, c.employe_id)
    if u is None:
        return titulaires_role(db, "PDG") - {c.employe_id}, True
    resp, unite_trouvee = responsable_unite(db, u, exclure={c.employe_id})
    return resp, unite_trouvee != u


def decideurs(db: Session, c: Conge) -> tuple[set[int], bool]:
    """Le RH décide ; si le RH est le demandeur, remontée au PDG."""
    rh = titulaires_role(db, "RH") - {c.employe_id}
    return (rh, False) if rh else (titulaires_role(db, "PDG") - {c.employe_id}, True)


def _sortie(db: Session, c: Conge, e: Employe, type_libelle: str, d: Droits) -> dict:
    a_traiter = False
    attente = []
    if c.statut == "en attente avis":
        ids, _ = donneurs_avis(db, c)
        attente, a_traiter = noms(db, ids), d.employe_id in ids or d.superutilisateur
    elif c.statut == "en attente RH":
        ids, _ = decideurs(db, c)
        attente, a_traiter = noms(db, ids), d.employe_id in ids or d.superutilisateur
    return {"id": c.id, "employe_id": e.id, "employe": _nom(e), "type_absence_id": c.type_absence_id, "type": type_libelle,
            "date_debut": str(c.date_debut), "date_fin": str(c.date_fin), "nb_jours": float(c.nb_jours), "motif": c.motif,
            "avis_responsable": c.avis_responsable, "motif_avis": c.motif_avis, "avis_remonte": c.avis_remonte,
            "decision_rh": c.decision_rh, "motif_decision": c.motif_decision, "statut": c.statut,
            "en_attente_de": attente, "a_traiter_par_moi": a_traiter}


@router.get("/conges")
def lister_conges(a_traiter: bool = False, statut: str | None = None, employe_id: int | None = None,
                  db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    q = (select(Conge, Employe, TypeAbsence.libelle).join(Employe, Employe.id == Conge.employe_id)
         .join(TypeAbsence, TypeAbsence.id == Conge.type_absence_id).order_by(Conge.date_debut.desc()))
    if statut:
        q = q.where(Conge.statut == statut)
    if employe_id:
        q = q.where(Conge.employe_id == employe_id)
    res = []
    for c, e, t in db.execute(q).all():
        u = unite_principale(db, e.id)
        visible = e.id == d.employe_id or d.a_role(*GESTION) or (u is not None and d.voit_unite(u))
        if not visible:
            continue
        s = _sortie(db, c, e, t, d)
        if a_traiter and not s["a_traiter_par_moi"]:
            continue
        res.append(s)
    return res


@router.get("/conges/solde/{employe_id}")
def lire_solde(employe_id: int, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    if employe_id != d.employe_id and not d.a_role(*GESTION, "RESPONSABLE_ACTIVITE", "DIRECTEUR"):
        raise HTTPException(403, "Accès refusé")
    if not db.get(Employe, employe_id):
        raise HTTPException(404, "Employé introuvable")
    return solde(db, employe_id)


@router.post("/conges", status_code=201)
def demander(data: DemandeConge, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    employe_id = data.employe_id or d.employe_id
    if employe_id is None:
        raise HTTPException(400, "Indiquez l'employé concerné")
    if employe_id != d.employe_id and not d.a_role(*GESTION):
        raise HTTPException(403, "Vous ne pouvez demander un congé que pour vous-même")
    e = db.get(Employe, employe_id)
    t = db.get(TypeAbsence, data.type_absence_id)
    if not e or not t:
        raise HTTPException(404, "Employé ou type d'absence introuvable")
    if data.date_fin < data.date_debut:
        raise HTTPException(400, "La date de fin précède la date de début")
    nb = (data.date_fin - data.date_debut).days + 1  # décompte calendaire
    pc = db.scalar(select(ParametreConge)) or ParametreConge()
    chevauche = db.scalar(select(Conge.id).where(Conge.employe_id == employe_id, Conge.statut.in_(("accepté", "en attente avis", "en attente RH")),
                                                 Conge.date_debut <= data.date_fin, Conge.date_fin >= data.date_debut))
    if chevauche:
        raise HTTPException(400, "Une demande existe déjà sur ces dates")
    if t.decompte_solde:
        s = solde(db, employe_id, data.date_debut.year)
        if (data.date_debut - date.today()).days < pc.preavis_demande_jours:
            raise HTTPException(400, f"Préavis insuffisant : demande à faire au moins {pc.preavis_demande_jours} jours avant")
        if nb > pc.plafond_par_prise:
            raise HTTPException(400, f"{pc.plafond_par_prise} jours maximum par congé annuel (décision 17)")
        if s["prises_annuelles"] >= pc.prises_annuelles_max:
            raise HTTPException(400, f"{pc.prises_annuelles_max} congés annuels maximum par an (décision 17)")
        if s["anciennete_mois"] < pc.anciennete_min_mois:
            raise HTTPException(400, f"Ancienneté minimale de {pc.anciennete_min_mois} mois non atteinte")
        if nb > s["solde"]:
            raise HTTPException(400, f"Solde insuffisant : {s['solde']} jours disponibles")
    c = Conge(employe_id=employe_id, type_absence_id=t.id, date_debut=data.date_debut, date_fin=data.date_fin, nb_jours=nb,
              motif=data.motif, statut="en attente avis", cree_par=d.utilisateur_id)
    db.add(c)
    db.flush()
    ids, remonte = donneurs_avis(db, c)
    c.avis_remonte = remonte
    notifier(db, ids, f"Demande de congé de {_nom(e)} ({nb} j) : votre avis est attendu", "/conges")
    db.commit()
    return _sortie(db, c, e, t.libelle, d)


@router.put("/conges/{conge_id}/avis")
def donner_avis(conge_id: int, data: Avis, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    c = db.get(Conge, conge_id)
    if not c or c.statut != "en attente avis":
        raise HTTPException(400, "Cette demande n'attend pas d'avis")
    ids, remonte = donneurs_avis(db, c)
    if d.employe_id not in ids and not d.superutilisateur:
        raise HTTPException(403, "L'avis revient à : " + ", ".join(noms(db, ids)))
    if data.avis == "défavorable" and not data.motif:
        raise HTTPException(400, "Motif obligatoire pour un avis défavorable")
    c.avis_responsable, c.motif_avis, c.avis_par = data.avis, data.motif, d.employe_id
    c.date_avis, c.avis_remonte, c.statut = datetime.now(timezone.utc), remonte, "en attente RH"
    rh, _ = decideurs(db, c)
    e = db.get(Employe, c.employe_id)
    notifier(db, rh, f"Congé de {_nom(e)} : avis {data.avis}, décision RH attendue", "/conges")
    db.commit()
    return _sortie(db, c, e, db.get(TypeAbsence, c.type_absence_id).libelle, d)


@router.put("/conges/{conge_id}/decision")
def decider(conge_id: int, data: Decision, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    c = db.get(Conge, conge_id)
    if not c or c.statut != "en attente RH":
        raise HTTPException(400, "Cette demande n'attend pas de décision RH")
    ids, _ = decideurs(db, c)
    if d.employe_id not in ids and not d.superutilisateur:
        raise HTTPException(403, "La décision revient à : " + ", ".join(noms(db, ids)))
    t = db.get(TypeAbsence, c.type_absence_id)
    if data.decision == "accepté" and t.decompte_solde:
        s = solde(db, c.employe_id, c.date_debut.year)
        if float(c.nb_jours) > s["solde"]:
            raise HTTPException(400, f"Solde insuffisant au moment de la décision : {s['solde']} jours")
    if data.decision == "refusé" and not data.motif:
        raise HTTPException(400, "Motif obligatoire pour un refus")
    c.decision_rh, c.motif_decision, c.decide_par = data.decision, data.motif, d.employe_id
    c.date_decision, c.statut = datetime.now(timezone.utc), data.decision
    e = db.get(Employe, c.employe_id)
    destinataires = {c.employe_id} | ({c.avis_par} if c.avis_par else set())
    notifier(db, destinataires, f"Congé de {_nom(e)} du {c.date_debut.strftime('%d/%m')} : {data.decision}", "/conges")
    db.commit()
    return _sortie(db, c, e, t.libelle, d)


@router.put("/conges/{conge_id}/annuler")
def annuler(conge_id: int, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    c = db.get(Conge, conge_id)
    if not c:
        raise HTTPException(404, "Demande introuvable")
    if c.employe_id != d.employe_id and not d.a_role(*GESTION):
        raise HTTPException(403, "Seul le demandeur ou le RH peut annuler")
    if c.statut not in ("en attente avis", "en attente RH") and not (c.statut == "accepté" and c.date_debut > date.today() and d.a_role(*GESTION)):
        raise HTTPException(400, "Cette demande ne peut plus être annulée")
    c.statut = "annulé"
    db.commit()
    e = db.get(Employe, c.employe_id)
    return _sortie(db, c, e, db.get(TypeAbsence, c.type_absence_id).libelle, d)
