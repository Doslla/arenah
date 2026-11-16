"""Remplit la base avec les données de départ et l'historique (dataset IA ARENAH v1.x).

Usage (depuis backend/, venv activé) :
    python -m app.scripts.import_donnees --data ../data/dataset_ia_arenah_v1
    python -m app.scripts.import_donnees --data ../data/dataset_ia_arenah_v1 --reset   # vide d'abord les tables

Crée aussi les comptes : « admin » (superutilisateur) et un compte par employé
(mot de passe provisoire à changer à la première connexion).
"""
import argparse
import os
import sys
import unicodedata
from datetime import date, datetime, time

import pandas as pd
from sqlalchemy import func, insert, select, text

from app.core.config import settings
from app.core.security import hacher
from app.db.base import Base
from app.db.session import SessionLocal
from app.models import (
    AffectationCaisse, Affectation, Budget, Caisse, CategorieDepense, CategorieRecette, Cloture, CompteTresorerie,
    CritereEvaluation, Depense, Employe, EvenementCalendrier, ExerciceComptable, MouvementCaisse, Parametre,
    ParametreAlerte, ParametreConge, Poste, Presence, RemiseFonds, Role, TypeAbsence, TypeContrat, Unite, Utilisateur,
)

ROLES = [
    ("PDG", "Président-Directeur Général", True), ("DIRECTEUR", "Directeur", False), ("RH", "Ressources humaines", True),
    ("ASSISTANT_RH", "Assistant RH", True), ("COMPTABLE", "Comptable", True), ("ASSISTANT_COMPTABLE", "Assistant comptable", True),
    ("RESP_ACHATS", "Responsable Achats", True), ("RESPONSABLE_ACTIVITE", "Responsable d'activité", False),
    ("CAISSIER", "Caissier", False), ("EMPLOYE", "Employé", False), ("ADMIN_INFO", "Administrateur informatique", True),
]
TYPES_CONTRAT = [("CDI", False, 30), ("CDD", True, 15), ("Période d'essai", True, 0), ("Stage", True, 0), ("Extra / journalier", True, 0)]
TYPES_ABSENCE = [("Congé annuel", True, False), ("Maladie", False, True), ("Maternité", False, True), ("Paternité", False, True),
                 ("Deuil", False, True), ("Permission", False, False)]
CRITERES = [("Assiduité", 1.0), ("Rapidité", 1.0), ("Qualité du service", 1.5), ("Remarques clients", 1.0)]
# (clé, valeur par défaut, type, description, modifiable par)
PARAMETRES_DEFAUT = [
    ("devise", "Ar", "texte", "Devise d'affichage", "PDG,ADMIN_INFO"),
    ("exercice_courant", "2026", "entier", "Exercice comptable en cours (année civile)", "COMPTABLE,PDG"),
    ("heure_debut_defaut", "08:00", "texte", "Heure d'arrivée prévue par défaut (sans planning)", "RH,PDG"),
    ("tolerance_retard_min", "10", "entier", "Tolérance de retard en minutes (décision 15)", "RH,PDG"),
    ("delai_justificatif_heures", "48", "entier", "Délai pour justifier une absence (décision 16)", "RH,PDG"),
    ("absences_avant_avertissement", "3", "entier", "Absences injustifiées du mois avant proposition d'avertissement", "RH,PDG"),
    ("avance_max_pourcent", "50", "entier", "Avance maximale en % du salaire du mois (décision 25)", "COMPTABLE,PDG"),
    ("prime_plafond_ar", "500000", "entier", "Plafond d'une prime (décision 30, à confirmer)", "PDG"),
    ("heure_cloture_caisse", "20:00", "texte", "Heure de rappel de clôture des caisses", "COMPTABLE,PDG"),
    ("ecart_caisse_alerte_ar", "10000", "entier", "Écart de clôture au-delà duquel une alerte est créée", "COMPTABLE,PDG"),
    ("seuil_alerte_budget_pourcent", "80", "entier", "Alerte quand le budget du mois est consommé à ce % ", "COMPTABLE,PDG"),
]
CORRESPONDANCE_GENERAUX = {  # parametres_generaux.csv → clé de la plateforme
    "jour_repos_personnel": ("jour_repos_personnel", "texte", "RH,PDG"),
    "ouvrir_jour_repos_si_ferie": ("ouvrir_jour_repos_si_ferie", "booleen", "RH,PDG"),
    "unites_sans_repos": ("unites_sans_repos", "texte", "RH,PDG"),
    "jour_remise": ("jour_remise_caisse", "texte", "COMPTABLE,PDG"),
    "seuil_pdg_ar": ("seuil_validation_pdg_ar", "entier", "PDG"),
}


def sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def lire(dossier, *chemin, **kw):
    p = os.path.join(dossier, *chemin)
    if not os.path.exists(p):
        sys.exit(f"Fichier introuvable : {p}")
    return pd.read_csv(p, **kw)


def vider(db):
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables if t.name != "journal_audit")
    db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    db.commit()
    print("Tables vidées (le journal d'audit est conservé).")


def importer(dossier: str, reset: bool):
    db = SessionLocal()
    db.info["import"] = True  # le trigger d'audit ignore les lignes importées
    if reset:
        vider(db)
    if db.scalar(select(Unite.id).limit(1)):
        sys.exit("La base contient déjà des données. Relancez avec --reset pour tout réimporter.")

    params = os.path.join(dossier, "parametres")
    ref = os.path.join(dossier, "00_referentiel")

    # ---------- Référentiels
    db.add_all([Role(code=c, libelle=l, portee_globale=g) for c, l, g in ROLES])
    db.add_all([TypeContrat(libelle=l, a_date_fin=f, preavis_jours=p) for l, f, p in TYPES_CONTRAT])
    db.add_all([TypeAbsence(libelle=l, decompte_solde=s, justificatif_requis=j) for l, s, j in TYPES_ABSENCE])
    db.add_all([CritereEvaluation(libelle=l, poids=p) for l, p in CRITERES])
    db.add(ParametreConge())
    db.add_all([CompteTresorerie(nom="Coffre", type="coffre"), CompteTresorerie(nom="Banque", type="banque")])
    gen = lire(params, "parametres_generaux.csv", dtype=str).set_index("cle")
    vus = set()
    for cle_src, (cle, typ, qui) in CORRESPONDANCE_GENERAUX.items():
        if cle_src in gen.index:
            db.add(Parametre(cle=cle, valeur=gen.loc[cle_src, "valeur"], type=typ, description=gen.loc[cle_src, "description"], modifiable_par=qui))
            vus.add(cle)
    for cle, val, typ, desc, qui in PARAMETRES_DEFAUT:
        if cle not in vus:
            db.add(Parametre(cle=cle, valeur=val, type=typ, description=desc, modifiable_par=qui))
    cal = lire(params, "calendrier.csv", parse_dates=["debut", "fin"])
    db.add_all([EvenementCalendrier(date_debut=r.debut.date(), date_fin=r.fin.date(), type=r.type, libelle=r.libelle, fiabilite=r.fiabilite)
                for r in cal.itertuples()])
    db.flush()
    print(f"Référentiels, {db.scalar(select(func.count(Parametre.id)))} paramètres, {len(cal)} événements du calendrier")

    # ---------- Organisation
    un = lire(ref, "unites.csv").fillna({"parent": ""})
    ids_unite: dict[str, int] = {}
    for i, r in enumerate(un.itertuples()):
        u = Unite(nom=r.nom, type=r.type, parent_id=ids_unite.get(r.parent) if r.parent else None, encaisse=bool(r.encaisse), ordre_affichage=i)
        db.add(u)
        db.flush()
        ids_unite[r.nom] = u.id
    roles = {r.code: r.id for r in db.scalars(select(Role))}
    po = lire(ref, "postes.csv")
    ids_poste = {}
    for r in po.itertuples():
        p = Poste(intitule=r.intitule, unite_id=ids_unite[r.unite], role_id=roles[r.role], est_responsable=bool(r.est_responsable))
        db.add(p)
        db.flush()
        ids_poste[r.poste_id] = p.id
    em = lire(ref, "employes.csv")
    ids_emp = {}
    for r in em.itertuples():
        e = Employe(matricule=r.matricule, nom=r.nom_usuel, prenom="", civilite=r.civilite if isinstance(r.civilite, str) else "",
                    date_embauche=date.fromisoformat(r.date_embauche), statut=r.statut)
        db.add(e)
        db.flush()
        ids_emp[r.employe_id] = e.id
    af = lire(ref, "affectations.csv")
    for r in af.itertuples():
        db.add(Affectation(employe_id=ids_emp[r.employe_id], poste_id=ids_poste[r.poste_id], date_debut=date.fromisoformat(r.date_debut),
                           est_interim=bool(r.est_interim), motif="Organigramme nominatif du 09/10/2026"))
    print(f"{len(un)} unités, {len(po)} postes, {len(em)} employés, {len(af)} affectations")

    # ---------- Comptes utilisateurs
    db.add(Utilisateur(login="admin", mot_de_passe_hash=hacher(settings.admin_password), est_superutilisateur=True, doit_changer_mdp=True))
    hash_prov = hacher(settings.mot_de_passe_provisoire)
    logins = []
    for r in em.itertuples():
        login = sans_accents(r.nom_usuel).lower().replace(" ", "")
        db.add(Utilisateur(employe_id=ids_emp[r.employe_id], login=login, mot_de_passe_hash=hash_prov, doit_changer_mdp=True))
        logins.append(login)
    print(f"Comptes : admin + {len(logins)} employés ({', '.join(logins)})")

    # ---------- Caisses
    cs = lire(ref, "caisses.csv")
    ids_caisse = {}
    for r in cs.itertuples():
        c = Caisse(nom=r.nom, unite_id=ids_unite[r.unite], fonds=int(r.fonds_ar))
        db.add(c)
        db.flush()
        ids_caisse[r.nom] = c.id
        caissiers = po[(po.unite == r.unite) & (po.role == "CAISSIER")].poste_id
        for a in af[af.poste_id.isin(caissiers)].itertuples():
            db.add(AffectationCaisse(caisse_id=c.id, employe_id=ids_emp[a.employe_id], date_debut=date.fromisoformat(a.date_debut)))
    caisse_par_unite = {r.unite: ids_caisse[r.nom] for r in cs.itertuples()}

    # ---------- Exercices, catégories
    db.add_all([ExerciceComptable(libelle="2025", date_debut=date(2025, 1, 1), date_fin=date(2025, 12, 31), statut="clôturé"),
                ExerciceComptable(libelle="2026", date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31), statut="ouvert")])
    enc = lire(dossier, "01_encaissements", "encaissements_journaliers.csv", parse_dates=["date"])
    dep = lire(dossier, "03_depenses_budget", "depenses.csv", parse_dates=["date"])
    bud = lire(dossier, "03_depenses_budget", "budget_2026.csv")
    ids_cat_rec = {}
    for (act, cat), _ in enc.groupby(["activite", "categorie_recette"]):
        c = CategorieRecette(libelle=cat, unite_id=ids_unite[act])
        db.add(c)
        db.flush()
        ids_cat_rec[(act, cat)] = c.id
    ids_cat_dep = {}
    for cat in sorted(set(dep.categorie) | set(bud.categorie) | {"Divers"}):
        c = CategorieDepense(libelle=cat)
        db.add(c)
        db.flush()
        ids_cat_dep[cat] = c.id
    db.add(ParametreAlerte(type="budget", seuil=80, roles_destinataires="COMPTABLE,PDG"))
    db.add(ParametreAlerte(type="écart caisse", seuil=10000, roles_destinataires="COMPTABLE"))
    db.commit()

    # ---------- Historique : encaissements (totaux journaliers par catégorie)
    e = enc[enc.montant_ar > 0]
    db.execute(insert(MouvementCaisse), [{
        "caisse_id": caisse_par_unite[r.activite], "type": "encaissement", "categorie_recette_id": ids_cat_rec[(r.activite, r.categorie_recette)],
        "montant": int(r.montant_ar), "nb_transactions": int(r.nb_transactions), "date_heure": datetime.combine(r.date.date(), time(18, 0)),
        "motif": "Total journalier importé", "source": r.source} for r in e.itertuples()])
    so = lire(dossier, "02_caisses", "sorties_caisse.csv", parse_dates=["date"])
    db.execute(insert(MouvementCaisse), [{
        "caisse_id": ids_caisse[r.caisse], "type": "sortie", "categorie_depense_id": ids_cat_dep["Divers"], "montant": int(r.montant_ar),
        "date_heure": datetime.combine(r.date.date(), time(15, 0)), "motif": r.motif, "source": r.source} for r in so.itertuples()])
    cl = lire(dossier, "02_caisses", "clotures.csv", parse_dates=["date"])
    db.execute(insert(Cloture), [{
        "caisse_id": ids_caisse[r.caisse], "date": r.date.date(), "fonds": int(r.fonds_ar), "report": int(r.report_ar),
        "total_encaissements": int(r.encaissements_ar), "total_sorties": int(r.sorties_ar), "montant_theorique": int(r.montant_theorique_ar),
        "montant_compte": int(r.montant_compte_ar), "ecart": int(r.ecart_ar), "statut": r.statut, "source": r.source} for r in cl.itertuples()])
    db.execute(text("""UPDATE mouvement_caisse m SET cloture_id = c.id FROM cloture c
                       WHERE c.caisse_id = m.caisse_id AND c.date = m.date_heure::date"""))
    re_ = lire(dossier, "02_caisses", "remises_fonds.csv", parse_dates=["date"])
    clo_ids = {(cid, d): i for i, cid, d in db.execute(select(Cloture.id, Cloture.caisse_id, Cloture.date)).all()}
    db.execute(insert(RemiseFonds), [{
        "caisse_id": ids_caisse[r.caisse], "cloture_id": clo_ids.get((ids_caisse[r.caisse], r.date.date())), "montant": int(r.montant_ar),
        "date_heure": datetime.combine(r.date.date(), time(20, 0)), "confirmee": True, "source": r.source} for r in re_.itertuples()])
    print(f"Caisses : {len(e)} encaissements journaliers, {len(so)} sorties, {len(cl)} clôtures, {len(re_)} remises")

    # ---------- Historique : dépenses et budget
    statut_ok = {"payée": "payée", "refusée": "refusée", "en étude achats": "en étude achats", "à valider comptable": "à valider comptable", "à valider PDG": "à valider PDG"}
    db.execute(insert(Depense), [{
        "unite_id": ids_unite[r.unite], "categorie_depense_id": ids_cat_dep[r.categorie], "objet": str(r.objet)[:200], "date": r.date.date(),
        "montant_estime": int(r.montant_ar), "montant_reel": int(r.montant_ar) if r.statut == "payée" else None,
        "statut": statut_ok.get(r.statut, "payée"), "date_paiement": r.date.date() if r.statut == "payée" else None,
        "mode_paiement": "espèces" if r.statut == "payée" else None, "origine": "demande", "source": r.source} for r in dep.itertuples()])
    ex26 = db.scalar(select(ExerciceComptable.id).where(ExerciceComptable.libelle == "2026"))
    db.execute(insert(Budget), [{
        "exercice_id": ex26, "unite_id": ids_unite[r.unite], "categorie_depense_id": ids_cat_dep[r.categorie], "mois": int(r.mois),
        "montant_prevu": int(r.montant_prevu_ar), "version": int(r.version)} for r in bud.itertuples()])
    print(f"Dépenses : {len(dep)} lignes ; budget 2026 : {len(bud)} lignes")

    # ---------- Historique : présences
    pr = lire(dossier, "04_presences", "presences.csv", parse_dates=["date"])
    emp_par_nom = {r.nom_usuel: ids_emp[r.employe_id] for r in em.itertuples()}

    def dt(v):
        return None if pd.isna(v) or v == "" else datetime.strptime(v, "%Y-%m-%d %H:%M")
    db.execute(insert(Presence), [{
        "employe_id": emp_par_nom[r.employe], "unite_id": ids_unite[r.unite], "date": r.date.date(),
        "heure_prevue": datetime.strptime(r.heure_prevue, "%H:%M").time(), "heure_arrivee": dt(r.heure_arrivee), "heure_depart": dt(r.heure_depart),
        "statut": r.statut, "absence_justifiee": (str(r.absence_justifiee) == "True") if r.statut == "absent" else None,
        "source_saisie": r.source_saisie, "source": r.source} for r in pr.itertuples()])
    print(f"Présences : {len(pr)} pointages")
    db.commit()
    db.close()
    print("\nImport terminé. Connexion : admin /", settings.admin_password, " — employés : <login> /", settings.mot_de_passe_provisoire)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Import des données ARENAH")
    ap.add_argument("--data", required=True, help="Dossier dataset_ia_arenah_v1 (contenant parametres/, 00_referentiel/, ...)")
    ap.add_argument("--reset", action="store_true", help="Vider les tables avant l'import")
    a = ap.parse_args()
    importer(a.data, a.reset)
