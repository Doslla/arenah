"""Dépenses (décisions 3, 11, 22, 39) : responsable → Resp. Achats → comptable → PDG au-dessus du seuil.
Budget (décision 29) et alerte anticipée de dépassement avant validation (DIR-21)."""
import datetime as dt
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.core.deps import droits_courants, exiger_roles
from app.db.session import get_db
from app.models import (
    Budget, CategorieDepense, CompteTresorerie, Depense, Employe, ExerciceComptable, MouvementTresorerie, Unite, ValidationDepense,
)
from app.services.circuits import noms, notifier, parametre, titulaires_role
from app.services.droits import Droits

router = APIRouter(tags=["Dépenses et budget"])
ETAPES = {"resp_achats": ("RESP_ACHATS", "en étude achats", "Étude Resp. Achats"),
          "comptable": ("COMPTABLE", "à valider comptable", "Validation comptable"),
          "pdg": ("PDG", "à valider PDG", "Validation PDG")}
ENGAGES = ("validée", "payée")


class NouvelleDepense(BaseModel):
    unite_id: int
    categorie_depense_id: int
    objet: str = Field(min_length=3, max_length=200)
    montant_estime: int = Field(gt=0)
    date: dt.date | None = None
    urgence: bool = False


class Validation(BaseModel):
    decision: str = Field(pattern="^(accepté|refusé|partiel)$")
    montant_accepte: int | None = Field(default=None, gt=0)
    motif: str | None = None


class Paiement(BaseModel):
    montant_reel: int = Field(gt=0)
    mode_paiement: str = "espèces"


class LigneBudget(BaseModel):
    exercice: int
    unite_id: int
    categorie_depense_id: int
    mois: int = Field(ge=1, le=12)
    montant_prevu: int = Field(ge=0)


def seuil_pdg(db: Session, dep: Depense) -> int:
    u = db.get(Unite, dep.unite_id)
    return u.seuil_depense_pdg if u and u.seuil_depense_pdg else int(parametre(db, "seuil_validation_pdg_ar", "1000000"))


def circuit(db: Session, dep: Depense) -> list[dict]:
    """Étapes résolues au moment présent. Si le demandeur détient le rôle d'une étape, elle est retirée et le PDG
    valide en dernier, une seule fois (décision 39)."""
    montant = dep.montant_estime
    codes = ["resp_achats", "comptable"] + (["pdg"] if montant > seuil_pdg(db, dep) else [])
    exclus = {dep.demandeur_id} if dep.demandeur_id else set()
    etapes, remontee = [], False
    for code in codes:
        role = ETAPES[code][0]
        valideurs = titulaires_role(db, role) - exclus
        if not valideurs:  # le demandeur est le seul titulaire du rôle
            if code == "pdg":
                raise HTTPException(400, "Le PDG ne peut pas valider sa propre dépense : règle à définir (point ouvert du registre)")
            remontee = True
            continue
        etapes.append({"code": code, "valideurs": valideurs, "remontee": False})
    if remontee and not any(e["code"] == "pdg" for e in etapes):
        pdg = titulaires_role(db, "PDG") - exclus
        if not pdg:
            raise HTTPException(400, "Aucun valideur disponible pour la remontée")
        etapes.append({"code": "pdg", "valideurs": pdg, "remontee": True})
    faites = {v.etape: v for v in db.scalars(select(ValidationDepense).where(ValidationDepense.depense_id == dep.id).order_by(ValidationDepense.id))}
    for e in etapes:
        v = faites.get(e["code"])
        e["fait"] = bool(v and v.decision in ("accepté", "partiel"))
        e["decision"] = v.decision if v else None
        e["par"] = noms(db, {v.valideur_id})[0] if v else None
        e["date"] = v.date.strftime("%d/%m/%Y %H:%M") if v else None
        e["motif"] = v.motif if v else None
        e["libelle"] = ETAPES[e["code"]][2]
    return etapes


def etape_courante(etapes: list[dict]) -> dict | None:
    return next((e for e in etapes if not e["fait"]), None)


def controle_budget(db: Session, dep: Depense) -> dict | None:
    """Projection : dépenses engagées du mois + cette dépense, comparées au budget du mois (alerte anticipée)."""
    ex = db.scalar(select(ExerciceComptable).where(ExerciceComptable.date_debut <= dep.date, ExerciceComptable.date_fin >= dep.date))
    if not ex:
        return None
    prevu = db.scalar(select(func.sum(Budget.montant_prevu)).where(Budget.exercice_id == ex.id, Budget.unite_id == dep.unite_id,
                                                                   Budget.categorie_depense_id == dep.categorie_depense_id, Budget.mois == dep.date.month))
    if not prevu:
        return {"budget_saisi": False, "message": "Pas de budget saisi pour ce mois et cette catégorie : alerte inactive (décision 29)"}
    engage = db.scalar(select(func.coalesce(func.sum(func.coalesce(Depense.montant_reel, Depense.montant_estime)), 0)).where(
        Depense.unite_id == dep.unite_id, Depense.categorie_depense_id == dep.categorie_depense_id, Depense.statut.in_(ENGAGES),
        extract("year", Depense.date) == dep.date.year, extract("month", Depense.date) == dep.date.month, Depense.id != dep.id))
    apres = engage + (dep.montant_reel or dep.montant_estime)
    taux = round(100 * apres / prevu)
    seuil = int(parametre(db, "seuil_alerte_budget_pourcent", "80"))
    niveau = "critique" if taux > 100 else ("attention" if taux >= seuil else "ok")
    return {"budget_saisi": True, "prevu": int(prevu), "deja_engage": int(engage), "apres_validation": int(apres), "taux": taux, "niveau": niveau,
            "message": f"Après validation : {taux} % du budget du mois ({int(apres):,} / {int(prevu):,} Ar)".replace(",", " ")}


def _sortie(db: Session, dep: Depense, d: Droits, detail: bool = False) -> dict:
    cat = db.get(CategorieDepense, dep.categorie_depense_id)
    s = {"id": dep.id, "date": str(dep.date), "unite_id": dep.unite_id, "unite": db.get(Unite, dep.unite_id).nom,
         "categorie_depense_id": dep.categorie_depense_id, "categorie": cat.libelle, "objet": dep.objet,
         "montant_estime": dep.montant_estime, "montant_reel": dep.montant_reel, "urgence": dep.urgence, "statut": dep.statut,
         "demandeur": noms(db, {dep.demandeur_id})[0] if dep.demandeur_id else None, "source": dep.source,
         "a_traiter_par_moi": False, "etape": None}
    if dep.statut in ("en étude achats", "à valider comptable", "à valider PDG") and dep.source == "saisie" or detail:
        try:
            et = circuit(db, dep)
        except HTTPException as e:
            et, s["erreur_circuit"] = [], e.detail
        cour = etape_courante(et) if dep.statut not in ("refusée", "validée", "payée") else None
        if cour:
            s["etape"] = cour["libelle"]
            s["a_traiter_par_moi"] = d.employe_id in cour["valideurs"] or d.superutilisateur
            s["en_attente_de"] = noms(db, cour["valideurs"])
        if detail:
            s["circuit"] = [{k: v for k, v in e.items() if k != "valideurs"} | {"valideurs": noms(db, e["valideurs"])} for e in et]
            s["controle_budget"] = controle_budget(db, dep)
            s["seuil_pdg"] = seuil_pdg(db, dep)
    elif dep.statut == "validée":
        s["a_traiter_par_moi"] = d.a_role("COMPTABLE")
        s["etape"] = "Paiement"
    return s


@router.get("/depenses")
def lister_depenses(a_traiter: bool = False, statut: str | None = None, unite_id: int | None = None, limite: int = 300,
                    db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    q = select(Depense).order_by(Depense.date.desc(), Depense.id.desc())
    if statut:
        q = q.where(Depense.statut == statut)
    if unite_id:
        q = q.where(Depense.unite_id == unite_id)
    if a_traiter:
        q = q.where(Depense.statut.in_(("en étude achats", "à valider comptable", "à valider PDG", "validée")), Depense.source == "saisie")
    res = []
    for dep in db.scalars(q.limit(min(limite, 2000))):
        if not (d.voit_unite(dep.unite_id) or dep.demandeur_id == d.employe_id):
            continue
        s = _sortie(db, dep, d)
        if a_traiter and not s["a_traiter_par_moi"]:
            continue
        res.append(s)
    return res


@router.get("/depenses/{depense_id}")
def lire_depense(depense_id: int, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    dep = db.get(Depense, depense_id)
    if not dep or not (d.voit_unite(dep.unite_id) or dep.demandeur_id == d.employe_id):
        raise HTTPException(404, "Dépense introuvable")
    return _sortie(db, dep, d, detail=True)


@router.post("/depenses", status_code=201)
def demander_depense(data: NouvelleDepense, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    """Le responsable de l'activité (ou la direction / l'administration) soumet la demande."""
    if not d.a_role("RESPONSABLE_ACTIVITE", "DIRECTEUR", "PDG", "COMPTABLE", "RESP_ACHATS", "RH", "ADMIN_INFO"):
        raise HTTPException(403, "Seuls les responsables peuvent demander une dépense")
    if not d.voit_unite(data.unite_id):
        raise HTTPException(403, "Unité hors de votre périmètre")
    if d.employe_id is None:
        raise HTTPException(400, "Le compte technique ne peut pas être demandeur")
    dep = Depense(unite_id=data.unite_id, categorie_depense_id=data.categorie_depense_id, objet=data.objet, montant_estime=data.montant_estime,
                  date=data.date or date.today(), urgence=data.urgence, demandeur_id=d.employe_id, origine="demande", statut="brouillon",
                  source="saisie", cree_par=d.utilisateur_id)
    db.add(dep)
    db.flush()
    cour = etape_courante(circuit(db, dep))
    dep.statut = ETAPES[cour["code"]][1]
    notifier(db, cour["valideurs"], f"Dépense à traiter : {dep.objet} ({dep.montant_estime:,} Ar)".replace(",", " "), "/depenses")
    db.commit()
    return _sortie(db, dep, d, detail=True)


@router.put("/depenses/{depense_id}/valider")
def valider_depense(depense_id: int, data: Validation, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    dep = db.get(Depense, depense_id)
    if not dep or dep.statut not in ("en étude achats", "à valider comptable", "à valider PDG"):
        raise HTTPException(400, "Cette dépense n'attend pas de validation")
    et = circuit(db, dep)
    cour = etape_courante(et)
    if d.employe_id not in cour["valideurs"] and not d.superutilisateur:
        raise HTTPException(403, "Cette étape revient à : " + ", ".join(noms(db, cour["valideurs"])))
    if data.decision in ("refusé", "partiel") and not data.motif:
        raise HTTPException(400, "Motif obligatoire")
    if data.decision == "partiel":
        if not data.montant_accepte or data.montant_accepte >= dep.montant_estime:
            raise HTTPException(400, "Montant accepté inférieur au montant demandé requis")
    db.add(ValidationDepense(depense_id=dep.id, etape=cour["code"], valideur_id=d.employe_id or min(cour["valideurs"]), decision=data.decision,
                             montant_accepte=data.montant_accepte, motif=data.motif, date=datetime.now(timezone.utc), remontee=cour["remontee"]))
    if data.decision == "refusé":
        dep.statut = "refusée"
        notifier(db, {dep.demandeur_id}, f"Dépense refusée : {dep.objet} — {data.motif}", "/depenses")
    else:
        if data.decision == "partiel":
            dep.montant_estime = data.montant_accepte
        db.flush()
        suivante = etape_courante(circuit(db, dep))
        if suivante:
            dep.statut = ETAPES[suivante["code"]][1]
            notifier(db, suivante["valideurs"], f"Dépense à traiter : {dep.objet} ({dep.montant_estime:,} Ar)".replace(",", " "), "/depenses")
        else:
            dep.statut = "validée"
            notifier(db, {dep.demandeur_id} | titulaires_role(db, "COMPTABLE"), f"Dépense validée, à payer : {dep.objet}", "/depenses")
    db.commit()
    return _sortie(db, dep, d, detail=True)


@router.put("/depenses/{depense_id}/payer")
def payer_depense(depense_id: int, data: Paiement, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles("COMPTABLE"))):
    dep = db.get(Depense, depense_id)
    if not dep or dep.statut != "validée":
        raise HTTPException(400, "Seule une dépense validée peut être payée")
    dep.statut, dep.montant_reel, dep.mode_paiement = "payée", data.montant_reel, data.mode_paiement
    dep.date_paiement, dep.payee_par = date.today(), d.employe_id
    coffre = db.scalar(select(CompteTresorerie).where(CompteTresorerie.type == "coffre"))
    if coffre:
        db.add(MouvementTresorerie(compte_id=coffre.id, sens="sortie", montant=data.montant_reel, objet="depense", objet_id=str(dep.id),
                                   date_heure=datetime.now().replace(microsecond=0), libelle=dep.objet))
    db.commit()
    return _sortie(db, dep, d, detail=True)


# ---------------------------------------------------------- Budget
def _exercice(db: Session, annee: int) -> ExerciceComptable:
    ex = db.scalar(select(ExerciceComptable).where(ExerciceComptable.libelle == str(annee)))
    if not ex:
        raise HTTPException(404, f"Exercice {annee} introuvable")
    return ex


@router.get("/budgets/synthese")
def synthese_budget(exercice: int | None = None, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    """Par unité et catégorie : prévu sur l'année, prévu à date, consommé, taux, mois courant."""
    exercice = exercice or date.today().year
    ex = _exercice(db, exercice)
    mois_courant = date.today().month if date.today().year == exercice else 12
    noms_u = dict(db.execute(select(Unite.id, Unite.nom)).all())
    noms_c = dict(db.execute(select(CategorieDepense.id, CategorieDepense.libelle)).all())
    lignes: dict[tuple, dict] = {}
    for b in db.scalars(select(Budget).where(Budget.exercice_id == ex.id)):
        if not d.voit_unite(b.unite_id):
            continue
        l = lignes.setdefault((b.unite_id, b.categorie_depense_id), {"unite_id": b.unite_id, "unite": noms_u[b.unite_id], "categorie_depense_id": b.categorie_depense_id,
                                                                      "categorie": noms_c[b.categorie_depense_id], "mois": {m: 0 for m in range(1, 13)},
                                                                      "consomme_mois": {m: 0 for m in range(1, 13)}, "ids": {}})
        l["mois"][b.mois] += b.montant_prevu
        l["ids"][b.mois] = b.id
    q = (select(Depense.unite_id, Depense.categorie_depense_id, extract("month", Depense.date), func.sum(func.coalesce(Depense.montant_reel, Depense.montant_estime)))
         .where(Depense.statut.in_(ENGAGES), Depense.date.between(ex.date_debut, ex.date_fin))
         .group_by(Depense.unite_id, Depense.categorie_depense_id, extract("month", Depense.date)))
    for u, c, m, total in db.execute(q).all():
        if (u, c) in lignes:
            lignes[(u, c)]["consomme_mois"][int(m)] += int(total)
    res = []
    for l in lignes.values():
        prevu_an = sum(l["mois"].values())
        prevu_date = sum(v for m, v in l["mois"].items() if m <= mois_courant)
        conso = sum(l["consomme_mois"].values())
        pm, cm = l["mois"][mois_courant], l["consomme_mois"][mois_courant]
        res.append({**{k: l[k] for k in ("unite_id", "unite", "categorie_depense_id", "categorie", "ids")},
                    "mois": l["mois"], "consomme_mois": l["consomme_mois"], "prevu_annuel": prevu_an, "prevu_a_date": prevu_date,
                    "consomme": conso, "taux_a_date": round(100 * conso / prevu_date) if prevu_date else None,
                    "prevu_mois_courant": pm, "consomme_mois_courant": cm, "taux_mois_courant": round(100 * cm / pm) if pm else None})
    return {"exercice": exercice, "mois_courant": mois_courant, "lignes": sorted(res, key=lambda x: (x["unite"], x["categorie"]))}


@router.post("/budgets", status_code=201)
def saisir_budget(data: LigneBudget, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles("COMPTABLE", "PDG"))):
    """Crée ou met à jour le montant prévu d'un mois (unité × catégorie × mois)."""
    ex = _exercice(db, data.exercice)
    if ex.statut != "ouvert":
        raise HTTPException(400, "Exercice clôturé")
    b = db.scalar(select(Budget).where(Budget.exercice_id == ex.id, Budget.unite_id == data.unite_id,
                                       Budget.categorie_depense_id == data.categorie_depense_id, Budget.mois == data.mois))
    if b:
        b.montant_prevu = data.montant_prevu
    else:
        b = Budget(exercice_id=ex.id, unite_id=data.unite_id, categorie_depense_id=data.categorie_depense_id, mois=data.mois, montant_prevu=data.montant_prevu)
        db.add(b)
    db.commit()
    return {"id": b.id, "montant_prevu": b.montant_prevu}
