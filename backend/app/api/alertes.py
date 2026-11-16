"""Alertes par règles (décision 8) et notifications dans l'application (décision 33)."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import extract, func, select, update
from sqlalchemy.orm import Session

from app.core.deps import droits_courants, exiger_roles, utilisateur_courant
from app.db.session import get_db
from app.models import Alerte, Budget, CategorieDepense, Cloture, Contrat, Depense, Employe, ExerciceComptable, Notification, Unite, Utilisateur
from app.api.presences import proposer_avertissements
from app.services.circuits import parametre
from app.services.droits import Droits

router = APIRouter(tags=["Alertes et notifications"])


class MajAlerte(BaseModel):
    statut: str = Field(pattern="^(vue|traitée)$")


def _creer(db: Session, existantes: set, **kw) -> int:
    cle = (kw["type"], kw.get("entite"), kw.get("entite_id"))
    if cle in existantes:
        return 0
    db.add(Alerte(**kw))
    existantes.add(cle)
    return 1


def recalculer_alertes(db: Session, jour: date | None = None) -> dict:
    jour = jour or date.today()
    existantes = {(a.type, a.entite, a.entite_id) for a in db.scalars(select(Alerte))}
    noms_u = dict(db.execute(select(Unite.id, Unite.nom)).all())
    n = {"budget": 0, "écart caisse": 0, "fin de contrat": 0, "fin d'essai": 0, "absences": 0}

    # 1. Budget du mois consommé au-delà du seuil (inactif tant que le budget n'est pas saisi)
    seuil = int(parametre(db, "seuil_alerte_budget_pourcent", "80"))
    ex = db.scalar(select(ExerciceComptable).where(ExerciceComptable.date_debut <= jour, ExerciceComptable.date_fin >= jour))
    if ex:
        prevu = {(u, c): int(m) for u, c, m in db.execute(select(Budget.unite_id, Budget.categorie_depense_id, func.sum(Budget.montant_prevu))
                                                         .where(Budget.exercice_id == ex.id, Budget.mois == jour.month)
                                                         .group_by(Budget.unite_id, Budget.categorie_depense_id)).all()}
        conso = db.execute(select(Depense.unite_id, Depense.categorie_depense_id, func.sum(func.coalesce(Depense.montant_reel, Depense.montant_estime)))
                           .where(Depense.statut.in_(("validée", "payée")), extract("year", Depense.date) == jour.year,
                                  extract("month", Depense.date) == jour.month).group_by(Depense.unite_id, Depense.categorie_depense_id)).all()
        cats = dict(db.execute(select(CategorieDepense.id, CategorieDepense.libelle)).all())
        for u, c, total in conso:
            p = prevu.get((u, c))
            if p and total >= p * seuil / 100:
                taux = round(100 * total / p)
                n["budget"] += _creer(db, existantes, type="budget", niveau="critique" if taux > 100 else "attention",
                                      message=f"{noms_u[u]} / {cats[c]} : {taux} % du budget de {jour.strftime('%m/%Y')} consommé",
                                      justification=f"{int(total):,} Ar engagés sur {p:,} Ar prévus (seuil {seuil} %)".replace(",", " "),
                                      entite="budget", entite_id=f"{u}-{c}-{jour.strftime('%Y-%m')}-{'100' if taux > 100 else 'seuil'}",
                                      unite_id=u, role_destinataire="COMPTABLE")

    # 2. Écarts de caisse à traiter
    for cl in db.scalars(select(Cloture).where(Cloture.statut == "écart à traiter", Cloture.date >= jour - timedelta(days=31))):
        n["écart caisse"] += _creer(db, existantes, type="écart caisse", niveau="attention",
                                    message=f"Écart de {cl.ecart:+,} Ar à la clôture du {cl.date.strftime('%d/%m/%Y')}".replace(",", " "),
                                    justification="Écart supérieur au seuil d'alerte", entite="cloture", entite_id=str(cl.id), role_destinataire="COMPTABLE")

    # 3. Fins de contrat et de période d'essai dans les 30 jours
    for c, e in db.execute(select(Contrat, Employe).join(Employe).where(Contrat.statut == "actif")).all():
        if c.date_fin and jour <= c.date_fin <= jour + timedelta(days=30):
            n["fin de contrat"] += _creer(db, existantes, type="fin de contrat", niveau="attention",
                                          message=f"Contrat de {e.nom} {e.prenom} : fin le {c.date_fin.strftime('%d/%m/%Y')}",
                                          entite="contrat", entite_id=str(c.id), role_destinataire="RH")
        if c.fin_periode_essai and jour <= c.fin_periode_essai <= jour + timedelta(days=30):
            n["fin d'essai"] += _creer(db, existantes, type="fin d'essai", niveau="info",
                                       message=f"Période d'essai de {e.nom} {e.prenom} : fin le {c.fin_periode_essai.strftime('%d/%m/%Y')}",
                                       entite="contrat-essai", entite_id=str(c.id), role_destinataire="RH")

    # 4. Absences non justifiées : avertissements proposés au RH
    n["absences"] = proposer_avertissements(db, jour)
    db.commit()
    return n


@router.post("/alertes/recalculer")
def recalculer(jour: date | None = None, db: Session = Depends(get_db),
               _: Droits = Depends(exiger_roles("COMPTABLE", "RH", "PDG", "DIRECTEUR", "ADMIN_INFO"))):
    return recalculer_alertes(db, jour)


@router.get("/alertes")
def lister_alertes(statut: str | None = None, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    q = select(Alerte).order_by(Alerte.date.desc()).limit(300)
    if statut:
        q = q.where(Alerte.statut == statut)
    res = []
    for a in db.scalars(q):
        pour_moi = d.superutilisateur or a.role_destinataire is None or a.role_destinataire in d.tous_roles or d.a_role("PDG")
        if pour_moi and (a.unite_id is None or d.voit_unite(a.unite_id)):
            res.append({"id": a.id, "type": a.type, "niveau": a.niveau, "message": a.message, "justification": a.justification,
                        "role_destinataire": a.role_destinataire, "date": a.date.strftime("%d/%m/%Y %H:%M"), "statut": a.statut})
    return res


@router.put("/alertes/{alerte_id}")
def maj_alerte(alerte_id: int, data: MajAlerte, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    a = db.get(Alerte, alerte_id)
    if not a:
        raise HTTPException(404, "Alerte introuvable")
    a.statut = data.statut
    if data.statut == "traitée":
        a.traitee_par = d.employe_id
    db.commit()
    return {"id": a.id, "statut": a.statut}


@router.get("/notifications")
def mes_notifications(non_lues: bool = False, db: Session = Depends(get_db), u: Utilisateur = Depends(utilisateur_courant)):
    q = select(Notification).where(Notification.utilisateur_id == u.id).order_by(Notification.date.desc()).limit(50)
    if non_lues:
        q = q.where(Notification.lue.is_(False))
    total = db.scalar(select(func.count(Notification.id)).where(Notification.utilisateur_id == u.id, Notification.lue.is_(False)))
    return {"non_lues": total, "notifications": [{"id": n.id, "message": n.message, "lien": n.lien, "lue": n.lue,
                                                   "date": n.date.strftime("%d/%m %H:%M")} for n in db.scalars(q)]}


@router.put("/notifications/tout-lire", status_code=204)
def tout_lire(db: Session = Depends(get_db), u: Utilisateur = Depends(utilisateur_courant)):
    db.execute(update(Notification).where(Notification.utilisateur_id == u.id, Notification.lue.is_(False)).values(lue=True))
    db.commit()
