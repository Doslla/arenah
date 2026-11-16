"""Indicateurs du tableau de bord, limités au périmètre de l'utilisateur."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import droits_courants
from app.db.session import get_db
from app.models import Affectation, Poste, Budget, Caisse, Cloture, CategorieDepense, Depense, Employe, ExerciceComptable, MouvementCaisse, Unite
from app.services.droits import Droits

router = APIRouter(tags=["Tableau de bord"])
STATUTS_ENGAGES = ("validée", "payée")


def _debut_mois(d: date) -> date:
    return d.replace(day=1)


@router.get("/tableau-de-bord")
def tableau_de_bord(jour: date | None = None, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    jour = jour or date.today()
    debut = _debut_mois(jour)
    debut_prec = _debut_mois(debut - timedelta(days=1))
    fin_prec = debut_prec + (jour - debut)  # même nombre de jours pour comparer
    portee = d.unites_portee
    noms = dict(db.execute(select(Unite.id, Unite.nom)).all())

    def filtre_unite(q, col):
        return q.where(col.in_(portee)) if portee is not None else q

    # Encaissements par activité (mois en cours vs même période du mois précédent)
    def encaissements(d1, d2):
        q = (select(Caisse.unite_id, func.sum(MouvementCaisse.montant))
             .join(Caisse, Caisse.id == MouvementCaisse.caisse_id)
             .where(MouvementCaisse.type == "encaissement", func.date(MouvementCaisse.date_heure).between(d1, d2))
             .group_by(Caisse.unite_id))
        return {u: int(m or 0) for u, m in db.execute(filtre_unite(q, Caisse.unite_id)).all()}

    enc, enc_prec = encaissements(debut, jour), encaissements(debut_prec, fin_prec)
    par_activite = sorted(
        [{"unite_id": u, "activite": noms[u], "montant": enc.get(u, 0), "mois_precedent": enc_prec.get(u, 0)} for u in set(enc) | set(enc_prec)],
        key=lambda x: -x["montant"])

    # Série des 30 derniers jours (tous encaissements du périmètre)
    q = (select(func.date(MouvementCaisse.date_heure), func.sum(MouvementCaisse.montant))
         .join(Caisse, Caisse.id == MouvementCaisse.caisse_id)
         .where(MouvementCaisse.type == "encaissement", func.date(MouvementCaisse.date_heure).between(jour - timedelta(days=29), jour))
         .group_by(func.date(MouvementCaisse.date_heure)).order_by(func.date(MouvementCaisse.date_heure)))
    serie = [{"date": str(j), "montant": int(m)} for j, m in db.execute(filtre_unite(q, Caisse.unite_id)).all()]

    # Budget de l'exercice en cours : prévu vs consommé (dépenses validées ou payées)
    ex = db.scalar(select(ExerciceComptable).where(ExerciceComptable.date_debut <= jour, ExerciceComptable.date_fin >= jour))
    budget = []
    if ex:
        qb = filtre_unite(select(Budget.unite_id, func.sum(Budget.montant_prevu)).where(Budget.exercice_id == ex.id).group_by(Budget.unite_id), Budget.unite_id)
        prevu = {u: int(m) for u, m in db.execute(qb).all()}
        qd = filtre_unite(select(Depense.unite_id, func.sum(func.coalesce(Depense.montant_reel, Depense.montant_estime)))
                          .where(Depense.statut.in_(STATUTS_ENGAGES), Depense.date.between(ex.date_debut, ex.date_fin)).group_by(Depense.unite_id), Depense.unite_id)
        conso = {u: int(m) for u, m in db.execute(qd).all()}
        for u in sorted(set(prevu) | set(conso), key=lambda x: noms[x]):
            p, c = prevu.get(u, 0), conso.get(u, 0)
            budget.append({"unite_id": u, "unite": noms[u], "prevu": p, "consomme": c, "taux": round(100 * c / p) if p else None})

    # Clôtures avec écart à traiter
    qc = filtre_unite(select(func.count(Cloture.id)).join(Caisse, Caisse.id == Cloture.caisse_id).where(Cloture.statut == "écart à traiter"), Caisse.unite_id)

    # Dernières dépenses
    qd = filtre_unite(select(Depense, CategorieDepense.libelle).join(CategorieDepense).where(Depense.date <= jour)
                      .order_by(Depense.date.desc(), Depense.id.desc()).limit(6), Depense.unite_id)
    dernieres = [{"id": dep.id, "date": str(dep.date), "objet": dep.objet, "unite": noms[dep.unite_id], "categorie": cat,
                  "montant": dep.montant_reel or dep.montant_estime, "statut": dep.statut} for dep, cat in db.execute(qd).all()]

    # Effectif actif du périmètre (employés ayant une affectation en cours dans les unités visibles)
    qe = select(func.count(func.distinct(Employe.id))).where(Employe.statut == "actif")
    if portee is not None:
        qe = (qe.join(Affectation, Affectation.employe_id == Employe.id).join(Poste, Poste.id == Affectation.poste_id)
              .where(Poste.unite_id.in_(portee), Affectation.date_debut <= jour, or_(Affectation.date_fin.is_(None), Affectation.date_fin >= jour)))

    total_prevu = sum(b["prevu"] for b in budget)
    total_conso = sum(b["consomme"] for b in budget)
    return {
        "jour": str(jour),
        "effectif_actif": db.scalar(qe),
        "encaissements_mois": sum(enc.values()),
        "encaissements_mois_precedent": sum(enc_prec.values()),
        "encaissements_par_activite": par_activite,
        "serie_30_jours": serie,
        "budget": {"exercice": ex.libelle if ex else None, "prevu": total_prevu, "consomme": total_conso,
                   "taux": round(100 * total_conso / total_prevu) if total_prevu else None, "par_unite": budget},
        "clotures_ecart_a_traiter": db.scalar(qc),
        "dernieres_depenses": dernieres,
    }
