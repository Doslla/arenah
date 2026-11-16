"""Caisses (décisions 5, 10, 26, 27) : encaissements, sorties, clôture quotidienne, remise hebdomadaire, écriture inverse."""
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import droits_courants, exiger_roles
from app.db.session import get_db
from app.models import (
    Alerte, Caisse, CategorieDepense, CategorieRecette, Cloture, CompteTresorerie, Correction, Employe, MouvementCaisse,
    MouvementTresorerie, RemiseFonds, Unite,
)
from app.services.circuits import noms, notifier_role, parametre, responsable_unite
from app.services.droits import Droits

router = APIRouter(tags=["Caisses"])
OPERATEURS = ("CAISSIER", "RESPONSABLE_ACTIVITE", "DIRECTEUR", "COMPTABLE", "ASSISTANT_COMPTABLE", "PDG", "ADMIN_INFO")
COMPTA = ("COMPTABLE", "ASSISTANT_COMPTABLE", "PDG")


class NouveauMouvement(BaseModel):
    type: str = Field(pattern="^(encaissement|sortie)$")
    montant: int = Field(gt=0)
    categorie_recette_id: int | None = None
    categorie_depense_id: int | None = None
    motif: str | None = None
    numero_piece: str | None = None


class NouvelleCloture(BaseModel):
    date: date
    montant_compte: int = Field(ge=0)
    explication: str | None = None


class Controle(BaseModel):
    statut: str = Field(pattern="^(contrôlée|écart à traiter)$")
    explication: str | None = None


class EcritureInverse(BaseModel):
    motif: str = Field(min_length=3)


def _caisse(db: Session, caisse_id: int, d: Droits) -> Caisse:
    c = db.get(Caisse, caisse_id)
    if not c:
        raise HTTPException(404, "Caisse introuvable")
    if not d.voit_unite(c.unite_id):
        raise HTTPException(403, "Caisse hors de votre périmètre")
    return c


def report_avant(db: Session, c: Caisse, jour: date) -> int:
    """Espèces au-delà du fonds restées en caisse depuis la dernière remise (décision 26)."""
    der = db.scalar(select(Cloture).where(Cloture.caisse_id == c.id, Cloture.date < jour).order_by(Cloture.date.desc()).limit(1))
    if not der:
        return 0
    remise = db.scalar(select(func.count(RemiseFonds.id)).where(RemiseFonds.cloture_id == der.id))
    return 0 if remise else der.montant_compte - c.fonds


def _mouvements(db: Session, c: Caisse, jour: date):
    q = (select(MouvementCaisse).where(MouvementCaisse.caisse_id == c.id, func.date(MouvementCaisse.date_heure) == jour)
         .order_by(MouvementCaisse.date_heure))
    return db.scalars(q).all()


@router.get("/caisses")
def lister_caisses(db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    noms_u = dict(db.execute(select(Unite.id, Unite.nom)).all())
    return [{"id": c.id, "nom": c.nom, "unite_id": c.unite_id, "unite": noms_u[c.unite_id], "fonds": c.fonds, "actif": c.actif}
            for c in db.scalars(select(Caisse).where(Caisse.actif).order_by(Caisse.id)) if d.voit_unite(c.unite_id)]


@router.get("/caisses/{caisse_id}/journee")
def journee(caisse_id: int, jour: date | None = None, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    jour = jour or date.today()
    c = _caisse(db, caisse_id, d)
    mvts = _mouvements(db, c, jour)
    cat_r = dict(db.execute(select(CategorieRecette.id, CategorieRecette.libelle)).all())
    cat_d = dict(db.execute(select(CategorieDepense.id, CategorieDepense.libelle)).all())
    enc = sum(m.montant for m in mvts if m.type == "encaissement")
    sor = sum(m.montant for m in mvts if m.type == "sortie")
    rep = report_avant(db, c, jour)
    clo = db.scalar(select(Cloture).where(Cloture.caisse_id == c.id, Cloture.date == jour))
    remise = db.scalar(select(RemiseFonds).where(RemiseFonds.cloture_id == clo.id)) if clo else None
    return {
        "caisse": {"id": c.id, "nom": c.nom, "fonds": c.fonds}, "date": str(jour), "report": rep,
        "total_encaissements": enc, "total_sorties": sor, "montant_theorique": c.fonds + rep + enc - sor,
        "jour_remise": parametre(db, "jour_remise_caisse", "dimanche"),
        "mouvements": [{"id": str(m.id), "heure": m.date_heure.strftime("%H:%M"), "type": m.type, "montant": m.montant,
                        "categorie": cat_r.get(m.categorie_recette_id) or cat_d.get(m.categorie_depense_id) or "",
                        "motif": m.motif, "numero_piece": m.numero_piece, "nb_transactions": m.nb_transactions, "source": m.source,
                        "autorise_par": noms(db, {m.autorise_par})[0] if m.autorise_par else None} for m in mvts],
        "cloture": None if not clo else {"id": clo.id, "montant_theorique": clo.montant_theorique, "montant_compte": clo.montant_compte,
                                         "ecart": clo.ecart, "statut": clo.statut, "explication": clo.explication},
        "remise": None if not remise else {"id": remise.id, "montant": remise.montant, "confirmee": remise.confirmee},
        "categories_recette": [{"id": i, "libelle": l} for i, l in db.execute(
            select(CategorieRecette.id, CategorieRecette.libelle).where(CategorieRecette.unite_id == c.unite_id)).all()],
    }


@router.post("/caisses/{caisse_id}/mouvements", status_code=201)
def ajouter_mouvement(caisse_id: int, data: NouveauMouvement, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*OPERATEURS))):
    c = _caisse(db, caisse_id, d)
    maintenant = datetime.now().replace(microsecond=0)
    if db.scalar(select(Cloture.id).where(Cloture.caisse_id == c.id, Cloture.date == maintenant.date())):
        raise HTTPException(400, "Journée déjà clôturée : seule une écriture inverse par le comptable est possible (décision 5)")
    autorise = None
    if data.type == "sortie":
        if not data.motif:
            raise HTTPException(400, "Motif obligatoire pour une sortie de caisse")
        theorique = journee(caisse_id, maintenant.date(), db, d)["montant_theorique"]
        if data.montant > theorique:
            raise HTTPException(400, f"Montant supérieur aux espèces disponibles ({theorique} Ar)")
        # Autorisation : responsable de l'activité ; si c'est le caissier lui-même, remontée au supérieur (décision 11)
        resp, _ = responsable_unite(db, c.unite_id, exclure={d.employe_id} if d.employe_id else set())
        autorise = min(resp) if resp else None
    elif data.categorie_recette_id is None:
        raise HTTPException(400, "Catégorie de recette obligatoire")
    m = MouvementCaisse(caisse_id=c.id, type=data.type, montant=data.montant, categorie_recette_id=data.categorie_recette_id,
                        categorie_depense_id=data.categorie_depense_id, motif=data.motif, numero_piece=data.numero_piece,
                        date_heure=maintenant, caissier_id=d.employe_id, autorise_par=autorise, source="saisie")
    db.add(m)
    db.commit()
    return {"id": str(m.id), "type": m.type, "montant": m.montant, "autorise_par": noms(db, {autorise})[0] if autorise else None}


@router.post("/caisses/{caisse_id}/cloture", status_code=201)
def cloturer(caisse_id: int, data: NouvelleCloture, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*OPERATEURS))):
    """Attendu = fonds + report + encaissements − sorties ; l'écart est calculé, les espèces restent en caisse."""
    c = _caisse(db, caisse_id, d)
    if data.date > date.today():
        raise HTTPException(400, "Impossible de clôturer une date future")
    if db.scalar(select(Cloture.id).where(Cloture.caisse_id == c.id, Cloture.date == data.date)):
        raise HTTPException(400, "Cette journée est déjà clôturée")
    j = journee(caisse_id, data.date, db, d)
    ecart = data.montant_compte - j["montant_theorique"]
    seuil = int(parametre(db, "ecart_caisse_alerte_ar", "10000"))
    if ecart and not data.explication:
        raise HTTPException(400, "Explication obligatoire quand il y a un écart")
    clo = Cloture(caisse_id=c.id, date=data.date, fonds=c.fonds, report=j["report"], total_encaissements=j["total_encaissements"],
                  total_sorties=j["total_sorties"], montant_theorique=j["montant_theorique"], montant_compte=data.montant_compte,
                  ecart=ecart, explication=data.explication, cloturee_par=d.employe_id,
                  statut="écart à traiter" if abs(ecart) > seuil else "soumise", source="saisie")
    db.add(clo)
    db.flush()
    for m in _mouvements(db, c, data.date):
        m.cloture_id = clo.id
    if abs(ecart) > seuil:
        db.add(Alerte(type="écart caisse", niveau="critique" if abs(ecart) > 5 * seuil else "attention",
                      message=f"{c.nom} : écart de {ecart:+,} Ar à la clôture du {data.date.strftime('%d/%m/%Y')}".replace(",", " "),
                      justification=f"Seuil d'alerte : {seuil} Ar", entite="cloture", entite_id=str(clo.id), unite_id=c.unite_id,
                      role_destinataire="COMPTABLE"))
        notifier_role(db, ["COMPTABLE"], f"Écart de caisse à traiter : {c.nom}", "/caisses")
    db.commit()
    return {"id": clo.id, "montant_theorique": clo.montant_theorique, "montant_compte": clo.montant_compte, "ecart": ecart, "statut": clo.statut}


@router.get("/clotures")
def lister_clotures(caisse_id: int | None = None, statut: str | None = None, limite: int = 60,
                    db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    q = select(Cloture, Caisse).join(Caisse, Caisse.id == Cloture.caisse_id).order_by(Cloture.date.desc(), Caisse.id).limit(min(limite, 500))
    if caisse_id:
        q = q.where(Cloture.caisse_id == caisse_id)
    if statut:
        q = q.where(Cloture.statut == statut)
    return [{"id": cl.id, "date": str(cl.date), "caisse_id": ca.id, "caisse": ca.nom, "fonds": cl.fonds, "report": cl.report,
             "total_encaissements": cl.total_encaissements, "total_sorties": cl.total_sorties, "montant_theorique": cl.montant_theorique,
             "montant_compte": cl.montant_compte, "ecart": cl.ecart, "statut": cl.statut, "explication": cl.explication}
            for cl, ca in db.execute(q).all() if d.voit_unite(ca.unite_id)]


@router.put("/clotures/{cloture_id}/controle")
def controler(cloture_id: int, data: Controle, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*COMPTA))):
    cl = db.get(Cloture, cloture_id)
    if not cl:
        raise HTTPException(404, "Clôture introuvable")
    cl.statut, cl.controlee_par, cl.date_controle = data.statut, d.employe_id, datetime.now(timezone.utc)
    if data.explication:
        cl.explication = f"{cl.explication or ''}\nContrôle : {data.explication}".strip()
    for a in db.scalars(select(Alerte).where(Alerte.entite == "cloture", Alerte.entite_id == str(cl.id))):
        a.statut, a.traitee_par = ("traitée" if data.statut == "contrôlée" else a.statut), d.employe_id
    db.commit()
    return {"id": cl.id, "statut": cl.statut}


@router.post("/caisses/{caisse_id}/remise", status_code=201)
def remettre(caisse_id: int, jour: date | None = None, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*OPERATEURS))):
    """Remise hebdomadaire au comptable : tout sauf le fonds (décision 26)."""
    jour = jour or date.today()
    c = _caisse(db, caisse_id, d)
    clo = db.scalar(select(Cloture).where(Cloture.caisse_id == c.id, Cloture.date == jour))
    if not clo:
        raise HTTPException(400, "Clôturez d'abord la journée avant la remise")
    if db.scalar(select(RemiseFonds.id).where(RemiseFonds.cloture_id == clo.id)):
        raise HTTPException(400, "Remise déjà faite pour cette clôture")
    montant = clo.montant_compte - c.fonds
    if montant <= 0:
        raise HTTPException(400, "Rien à remettre : le montant compté ne dépasse pas le fonds")
    r = RemiseFonds(caisse_id=c.id, cloture_id=clo.id, montant=montant, remis_par=d.employe_id,
                    date_heure=datetime.combine(jour, datetime.now().time().replace(microsecond=0)), source="saisie")
    db.add(r)
    notifier_role(db, ["COMPTABLE"], f"Remise de {montant:,} Ar de la {c.nom} à confirmer".replace(",", " "), "/caisses")
    db.commit()
    return {"id": r.id, "montant": montant}


@router.put("/remises/{remise_id}/confirmer")
def confirmer_remise(remise_id: int, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles(*COMPTA))):
    """Le comptable confirme : les espèces entrent dans le coffre (décision 27)."""
    r = db.get(RemiseFonds, remise_id)
    if not r or r.confirmee:
        raise HTTPException(400, "Remise introuvable ou déjà confirmée")
    r.confirmee, r.recu_par = True, d.employe_id
    coffre = db.scalar(select(CompteTresorerie).where(CompteTresorerie.type == "coffre"))
    if coffre:
        db.add(MouvementTresorerie(compte_id=coffre.id, sens="entrée", montant=r.montant, objet="remise_caisse", objet_id=str(r.id),
                                   date_heure=datetime.now().replace(microsecond=0), libelle=f"Remise caisse n°{r.caisse_id}"))
    db.commit()
    return {"id": r.id, "confirmee": True}


@router.get("/remises")
def lister_remises(a_confirmer: bool = False, db: Session = Depends(get_db), d: Droits = Depends(droits_courants)):
    q = select(RemiseFonds, Caisse).join(Caisse, Caisse.id == RemiseFonds.caisse_id).order_by(RemiseFonds.date_heure.desc()).limit(100)
    if a_confirmer:
        q = q.where(RemiseFonds.confirmee.is_(False))
    return [{"id": r.id, "caisse": c.nom, "date": str(r.date_heure.date()), "montant": r.montant, "confirmee": r.confirmee}
            for r, c in db.execute(q).all() if d.voit_unite(c.unite_id)]


@router.post("/mouvements/{mouvement_id}/ecriture-inverse", status_code=201)
def ecriture_inverse(mouvement_id: str, data: EcritureInverse, db: Session = Depends(get_db), d: Droits = Depends(exiger_roles("COMPTABLE"))):
    """Après clôture, aucune modification : le comptable passe une écriture inverse, tracée (décision 5)."""
    m = db.get(MouvementCaisse, mouvement_id)
    if not m:
        raise HTTPException(404, "Mouvement introuvable")
    if m.cloture_id is None:
        raise HTTPException(400, "Journée non clôturée : corrigez directement avec un motif")
    if d.employe_id is None:
        raise HTTPException(400, "Une écriture inverse doit être passée par un comptable nommé, pas par le compte technique")
    inv = MouvementCaisse(caisse_id=m.caisse_id, type=m.type, montant=-m.montant, categorie_recette_id=m.categorie_recette_id,
                          categorie_depense_id=m.categorie_depense_id, motif=f"Écriture inverse : {data.motif}",
                          date_heure=datetime.now().replace(microsecond=0), caissier_id=d.employe_id, source="correction")
    db.add(inv)
    db.add(Correction(entite="mouvement_caisse", entite_id=str(m.id), type="écriture inverse après clôture", motif=data.motif,
                      auteur_id=d.employe_id))
    db.commit()
    return {"id": str(inv.id), "montant": inv.montant}
