"""
ARENAH – Génération du jeu de données IA (v1)

Entrée  : dossier du dataset réel du Restaurant (v5 : restaurant_journalier.csv, achats.csv, ...)
Sortie  : dossier dataset_ia_arenah_v1/ (référentiel, encaissements, caisses, dépenses, budget, présences)

Principe (décision 31) : les données réelles sont gardées telles quelles (source = reel_*),
tout ce qui manque est généré et marqué source = synthetique. Les anomalies générées
sont listées dans anomalies_injectees.csv (vérité terrain pour évaluer l'Isolation Forest).

Usage : python generer_donnees_ia.py <dossier_dataset_reel> <dossier_sortie>
Toutes les hypothèses sont dans les CSV du dossier parametres/ (à côté du script) : modifiez-les puis relancez.
Autre dossier de paramètres : variable d'environnement ARENAH_PARAMS.
"""
import sys
import os
import math
import random
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

# ------------------------------------------------- PARAMÈTRES (CSV)
# Tous les réglages sont dans le dossier parametres/ : modifiez les CSV puis relancez.
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
DOSSIER_PARAMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parametres")


def charger_parametres(dossier):
    g = pd.read_csv(os.path.join(dossier, "parametres_generaux.csv"), dtype=str).set_index("cle").valeur.to_dict()
    cal = pd.read_csv(os.path.join(dossier, "calendrier.csv"), parse_dates=["debut", "fin"])
    act = pd.read_csv(os.path.join(dossier, "activites.csv"))
    cats = pd.read_csv(os.path.join(dossier, "categories_recettes.csv"))
    sais = pd.read_csv(os.path.join(dossier, "saisons.csv"))
    dep = pd.read_csv(os.path.join(dossier, "depenses_recurrentes.csv")).fillna({"suit_saison": ""})
    return g, cal, act, cats, sais, dep


_G, _CAL, _ACT, _CATS, _SAIS, _DEP = charger_parametres(os.environ.get("ARENAH_PARAMS", DOSSIER_PARAMS))
SEED = int(_G["graine"])
DEBUT = date.fromisoformat(_G["debut"])
FIN = date.fromisoformat(_G["fin"])
DEBUT_PRESENCES = date.fromisoformat(_G["debut_presences"])
SEUIL_PDG = int(_G["seuil_pdg_ar"])
FONDS_RESTAURANT = int(_G["fonds_restaurant_ar"])
TAUX_ANOMALIE_CLOTURE = float(_G["taux_anomalie_cloture"])
TAUX_ANOMALIE_ENCAISSEMENT = float(_G["taux_anomalie_encaissement"])
TAUX_FERMETURE = float(_G["taux_fermeture_imprevue"])
JOUR_REPOS = JOURS.index(_G["jour_repos_personnel"].strip().lower())
OUVRIR_REPOS_SI_FERIE = _G["ouvrir_jour_repos_si_ferie"].strip().lower() == "oui"
UNITES_SANS_REPOS = {x.strip() for x in str(_G.get("unites_sans_repos", "")).split("|") if x.strip()}
JOUR_REMISE = JOURS.index(_G["jour_remise"].strip().lower())


def _periodes(typ):
    return [(r.debut.date(), r.fin.date(), r.libelle) for r in _CAL[_CAL.type == typ].itertuples()]


FERIES = {}
for _a, _b, _n in _periodes("ferie"):
    for _k in range((_b - _a).days + 1):
        FERIES[_a + timedelta(days=_k)] = _n
GRANDES_FETES = _periodes("grande_fete")
VACANCES = _periodes("vacances_scolaires")
FERMETURES = {_a + timedelta(days=_k) for _a, _b, _n in _periodes("fermeture") for _k in range((_b - _a).days + 1)}

SAISONS = {r.profil: {m: float(getattr(r, f"m{m:02d}")) for m in range(1, 13)} for r in _SAIS.itertuples()}
ACTIVITES = {}
for r in _ACT.itertuples():
    ACTIVITES[r.activite] = {
        "fonds": int(r.fonds_ar), "semaine": [float(getattr(r, f"coef_{j}")) for j in JOURS],
        "ferie": float(r.coef_ferie), "grande_fete": float(r.coef_grande_fete), "vacances": float(r.coef_vacances),
        "saison": r.profil_saison, "tendance": (float(r.tendance_min), float(r.tendance_max)),
        "categories": dict(zip(_CATS[_CATS.activite == r.activite].categorie_recette, _CATS[_CATS.activite == r.activite].montant_moyen_jour_ar)),
    }
DEPENSES_UNITES = {}
for r in _DEP.itertuples():
    DEPENSES_UNITES.setdefault(r.unite, []).append((r.categorie, r.objet, float(r.montant_mensuel_ar), float(r.achats_par_mois), r.suit_saison))


def grande_fete(d):
    for a, b, nom in GRANDES_FETES:
        if a <= d <= b:
            return nom
    return ""


def est_ouvert(d, unite=None):
    """Fermé le jour de repos du personnel (sauf férié si autorisé) et les jours de fermeture générale."""
    if d in FERMETURES:
        return False
    if d.weekday() == JOUR_REPOS and unite not in UNITES_SANS_REPOS:
        return OUVRIR_REPOS_SI_FERIE and d in FERIES
    return True


def coef_evenement(cfg, d):
    c = 1.0
    if d in FERIES:
        c *= cfg["ferie"]
    if grande_fete(d):
        c *= cfg["grande_fete"]
    if en_vacances(d):
        c *= cfg["vacances"]
    return min(c, 4.0)


# --------------------------------------------------------------- OUTILS
rng = np.random.default_rng(SEED)
random.seed(SEED)


def jours(d1, d2):
    d = d1
    while d <= d2:
        yield d
        d += timedelta(days=1)


def arrondi(x, pas=500):
    return int(max(0, round(x / pas) * pas))


def en_vacances(d):
    for a, b, nom in VACANCES:
        if a <= d <= b:
            return nom
    return ""


def ecrire(df, dossier, nom):
    os.makedirs(dossier, exist_ok=True)
    df.to_csv(os.path.join(dossier, nom), index=False, encoding="utf-8")
    print(f"  {nom:38s} {len(df):6d} lignes")


# ------------------------------------------------------- 1. RÉFÉRENTIEL
def referentiel():
    """Unités, postes, employés et affectations d'après l'organigramme nominatif (photos du 09/10/2026)."""
    unites = []

    def u(nom, typ, parent, encaisse=False):
        unites.append({"unite_id": len(unites) + 1, "nom": nom, "type": typ, "parent": parent, "encaisse": encaisse})

    u("Direction générale", "direction", "")
    u("Direction de l'Administration Générale", "direction", "Direction générale")
    for dep in ["Ressources humaines", "Finance et comptabilité", "Commercial et marketing", "Achats et logistique", "Informatique et technologie", "Secrétariat"]:
        u(dep, "département", "Direction de l'Administration Générale")
    u("Direction d'Exploitation", "direction", "Direction générale")
    groupes = {
        "Groupe Restaurant / Hôtel": ["Restaurant", "Hôtel"],
        "Groupe Événementiel / Piscine / Aire de jeux": ["Événementiel", "Piscine", "Aire de jeux"],
        "Groupe Accueil / Sécurité et entretien / Ménage et cuisine": ["Accueil", "Sécurité et entretien", "Ménage et cuisine"],
        "Groupe Cyber / Coiffure / Pharmacie / Boutique": ["Cyber", "Coiffure", "Pharmacie", "Boutique"],
        "Groupe Sport": ["Salle de sport / Basket / Foot / Volley"],
    }
    ouvertes = {"Restaurant", "Accueil", "Piscine", "Cyber", "Coiffure", "Ménage et cuisine"}  # décision 28 (à confirmer)
    for g, acts in groupes.items():
        u(g, "groupe", "Direction d'Exploitation")
        for a in acts:
            u(a, "activité", g, a in ouvertes)
    df_u = pd.DataFrame(unites)

    # (unité, intitulé, rôle, responsable ?, titulaire(s) — vide = à définir)
    P = [
        ("Direction générale", "PDG", "PDG", True, "Narindra"),
        ("Direction générale", "Conseiller", "EMPLOYE", False, "Amboara"),
        ("Direction générale", "Secrétaire", "EMPLOYE", False, ""),
        ("Direction de l'Administration Générale", "Directeur", "DIRECTEUR", True, "Amboara"),
        ("Ressources humaines", "Directeur", "RH", True, "Amboara"),
        ("Ressources humaines", "Assistant", "ASSISTANT_RH", False, ""),
        ("Finance et comptabilité", "Directeur", "COMPTABLE", True, "Amboara"),
        ("Finance et comptabilité", "Comptable", "COMPTABLE", False, ""),
        ("Finance et comptabilité", "Assistant", "ASSISTANT_COMPTABLE", False, ""),
        ("Commercial et marketing", "Directeur", "EMPLOYE", True, ""),
        ("Commercial et marketing", "Assistant", "EMPLOYE", False, ""),
        ("Commercial et marketing", "Community Manager", "EMPLOYE", False, ""),
        ("Achats et logistique", "Directeur", "RESP_ACHATS", True, "Mireille"),
        ("Achats et logistique", "Assistant", "EMPLOYE", False, ""),
        ("Achats et logistique", "Responsable stock", "EMPLOYE", False, ""),
        ("Informatique et technologie", "Directeur", "ADMIN_INFO", True, "Amboara"),
        ("Informatique et technologie", "Assistant", "EMPLOYE", False, ""),
        ("Secrétariat", "Secrétaire", "EMPLOYE", False, ""),
        ("Direction d'Exploitation", "Directrice", "DIRECTEUR", True, "Mireille"),
        ("Restaurant", "Chef", "RESPONSABLE_ACTIVITE", True, "Njaka"),
        ("Restaurant", "Aide cuisinier", "EMPLOYE", False, "Nirina"),
        ("Restaurant", "Caissier", "CAISSIER", False, "Faneva"),
        ("Restaurant", "Serveur", "EMPLOYE", False, "Mi"),
        ("Hôtel", "Gérant", "RESPONSABLE_ACTIVITE", True, "Nomace"),
        ("Hôtel", "Caissier", "CAISSIER", False, ""),
        ("Hôtel", "Femme de chambre", "EMPLOYE", False, ""),
        ("Hôtel", "Serveur", "EMPLOYE", False, ""),
        ("Événementiel", "Gérant", "RESPONSABLE_ACTIVITE", True, "Mireille"),
        ("Événementiel", "Assistant", "EMPLOYE", False, ""),
        ("Événementiel", "Logistique", "EMPLOYE", False, "Mireille"),
        ("Piscine", "Responsable", "RESPONSABLE_ACTIVITE", True, "Mampionona"),
        ("Aire de jeux", "Responsable", "RESPONSABLE_ACTIVITE", True, ""),
        ("Accueil", "Responsable", "RESPONSABLE_ACTIVITE", True, "Nomace"),
        ("Accueil", "Assistant", "EMPLOYE", False, "Aina"),
        ("Accueil", "Caissier", "CAISSIER", False, "Nomace"),
        ("Sécurité et entretien", "Gardien de jour", "EMPLOYE", False, "Dada Jean"),
        ("Sécurité et entretien", "Gardien de nuit", "EMPLOYE", False, "Faustin"),
        ("Sécurité et entretien", "Entretien", "EMPLOYE", False, "Faustin"),
        ("Sécurité et entretien", "Logistique", "EMPLOYE", False, "Dada Jean"),
        ("Ménage et cuisine", "Responsable", "RESPONSABLE_ACTIVITE", True, "Tsiory"),
        ("Ménage et cuisine", "Ménagère", "EMPLOYE", False, "Tahiry"),
        ("Ménage et cuisine", "Ménagère", "EMPLOYE", False, "Iris"),
        ("Cyber", "Responsable", "RESPONSABLE_ACTIVITE", True, "Nondy"),
        ("Cyber", "Caissier", "CAISSIER", False, "Nondy"),
        ("Coiffure", "Responsable", "RESPONSABLE_ACTIVITE", True, ""),
        ("Coiffure", "Coiffeur", "EMPLOYE", False, "Luanah"),
        ("Pharmacie", "Pharmacien", "EMPLOYE", False, ""),
        ("Pharmacie", "Docteur", "EMPLOYE", False, ""),
        ("Boutique", "Responsable", "RESPONSABLE_ACTIVITE", True, ""),
        ("Salle de sport / Basket / Foot / Volley", "Responsable", "RESPONSABLE_ACTIVITE", True, ""),
        ("Salle de sport / Basket / Foot / Volley", "Coach", "EMPLOYE", False, ""),
    ]
    noms = {"Narindra": ("Narindra", "Mme"), "Amboara": ("Amboara", "Mr")}
    personnes = []
    for *_, t in P:
        if t and t not in personnes:
            personnes.append(t)
    emp = []
    for i, n in enumerate(personnes, 1):
        emp.append({
            "employe_id": i, "matricule": f"ARN{i:03d}", "nom_usuel": n,
            "civilite": noms.get(n, (n, ""))[1], "statut": "actif",
            "date_embauche": "2025-01-06" if n in ("Narindra", "Amboara", "Mireille") else str(date(2025, 3, 3) + timedelta(days=int(rng.integers(0, 380)))),
        })
    df_e = pd.DataFrame(emp)
    id_emp = dict(zip(df_e.nom_usuel, df_e.employe_id))
    id_unite = dict(zip(df_u.nom, df_u.unite_id))
    postes, affs = [], []
    for k, (un, intit, role, resp, tit) in enumerate(P, 1):
        postes.append({"poste_id": k, "unite": un, "unite_id": id_unite[un], "intitule": intit, "role": role, "est_responsable": resp, "vacant": tit == ""})
        if tit:
            affs.append({"affectation_id": len(affs) + 1, "employe_id": id_emp[tit], "employe": tit, "poste_id": k,
                         "poste": f"{intit} – {un}", "date_debut": "2026-10-09", "date_fin": "", "est_interim": tit in ("Amboara", "Mireille")})
    df_p, df_a = pd.DataFrame(postes), pd.DataFrame(affs)
    caisses = [{"caisse_id": i, "nom": f"Caisse {a}", "unite": a, "fonds_ar": (FONDS_RESTAURANT if a == "Restaurant" else ACTIVITES[a]["fonds"])}
               for i, a in enumerate(["Restaurant"] + list(ACTIVITES), 1)]
    return df_u, df_p, df_e, df_a, pd.DataFrame(caisses)


# --------------------------------------------- 2. ENCAISSEMENTS JOURNALIERS
def encaissements(reel_journalier):
    lignes, anomalies = [], []
    # Restaurant : réel du 25/03 au 20/10, puis prolongation synthétique jusqu'à FIN
    rj = reel_journalier.copy()
    for _, r in rj.iterrows():
        lignes.append({"date": r.date.date(), "activite": "Restaurant", "categorie_recette": "Ventes restaurant",
                       "montant_ar": int(r.ca_ar), "nb_transactions": int(r.nb_tickets), "ouvert": bool(r.ouvert),
                       "anomalie_injectee": False, "source": "reel_caisse" if not r.jour_partiel else "reel_caisse_partiel",
                       "utilisable_entrainement": bool(r.utilisable_entrainement)})
    recent = rj[(rj.ouvert) & (~rj.jour_partiel) & (rj.date >= rj.date.max() - pd.Timedelta(days=56))]
    moy_jour = recent.groupby(recent.date.dt.weekday).ca_ar.median().to_dict()
    tick_moy = recent.ca_ar.sum() / max(1, recent.nb_tickets.sum())
    for d in jours(rj.date.max().date() + timedelta(days=1), FIN):
        wd = d.weekday()
        ouvert = est_ouvert(d) and rng.random() > TAUX_FERMETURE
        base = moy_jour.get(wd, recent.ca_ar.median()) * (2.5 if d in FERIES else 1.0) * (1.5 if grande_fete(d) else 1.0)
        m = arrondi(base * rng.lognormal(0, 0.35)) if ouvert else 0
        lignes.append({"date": d, "activite": "Restaurant", "categorie_recette": "Ventes restaurant", "montant_ar": m,
                       "nb_transactions": int(round(m / tick_moy)) if m else 0, "ouvert": ouvert,
                       "anomalie_injectee": False, "source": "synthetique", "utilisable_entrainement": True})

    # Autres activités : synthétique sur toute la période
    for act, cfg in ACTIVITES.items():
        tendance = rng.uniform(*cfg["tendance"])  # évolution annuelle
        n_jours = (FIN - DEBUT).days
        for i, d in enumerate(jours(DEBUT, FIN)):
            wd = d.weekday()
            ouvert = est_ouvert(d) and rng.random() > TAUX_FERMETURE
            facteur = cfg["semaine"][wd] * SAISONS[cfg["saison"]][d.month] * (1 + tendance * i / n_jours)
            facteur *= coef_evenement(cfg, d)
            anomalie = ouvert and rng.random() < TAUX_ANOMALIE_ENCAISSEMENT
            type_anom = rng.choice(["encaissement_sous_declare", "pic_anormal"]) if anomalie else ""
            for cat, niveau in cfg["categories"].items():
                m = niveau * facteur * rng.lognormal(0, 0.28) if ouvert else 0
                if type_anom == "encaissement_sous_declare":
                    m *= rng.uniform(0.2, 0.45)
                elif type_anom == "pic_anormal":
                    m *= rng.uniform(2.8, 4.0)
                m = arrondi(m)
                lignes.append({"date": d, "activite": act, "categorie_recette": cat, "montant_ar": m,
                               "nb_transactions": max(1, int(m / rng.uniform(4_000, 9_000))) if m else 0, "ouvert": ouvert,
                               "anomalie_injectee": bool(anomalie), "source": "synthetique", "utilisable_entrainement": True})
            if anomalie:
                anomalies.append({"date": d, "activite": act, "table": "encaissements_journaliers", "type": type_anom,
                                  "description": "montant du jour multiplié par un facteur anormal"})
    df = pd.DataFrame(lignes).sort_values(["date", "activite", "categorie_recette"]).reset_index(drop=True)
    df.insert(0, "encaissement_id", range(1, len(df) + 1))
    df["jour_semaine"] = pd.to_datetime(df.date).dt.weekday
    df["ferie"] = df.date.map(lambda d: FERIES.get(d, ""))
    df["grande_fete"] = df.date.map(grande_fete)
    df["vacances_scolaires"] = df.date.map(en_vacances)
    return df, anomalies


# ------------------------------------------- 3. SORTIES, CLÔTURES, REMISES
def caisses(df_enc, achats_reels, caisses_ref):
    sorties, clotures, remises, anomalies = [], [], [], []
    jour_ca = df_enc.groupby(["activite", "date"]).agg(ca=("montant_ar", "sum"), ouvert=("ouvert", "max")).reset_index()
    retraits = achats_reels[achats_reels.categorie == "retrait_caisse"]
    for _, cs in caisses_ref.iterrows():
        act, fonds = cs.unite, int(cs.fonds_ar)
        jc = jour_ca[jour_ca.activite == act].sort_values("date")
        report = 0
        for _, r in jc.iterrows():
            d = r.date
            if not r.ouvert:
                continue
            s_jour = 0
            # sorties réelles (retraits notés dans le cahier du Restaurant)
            if act == "Restaurant":
                for _, rr in retraits[retraits.date == str(d)].iterrows():
                    sorties.append({"date": d, "caisse": cs.nom, "motif": rr.libelle_cahier, "montant_ar": int(rr.prix_ar),
                                    "autorise_par": "Direction", "anomalie_injectee": False, "source": "reel_cahier"})
                    s_jour += int(rr.prix_ar)
            # petites sorties courantes
            for _ in range(rng.poisson(0.6)):
                mt = arrondi(rng.uniform(3_000, 35_000))
                mt = min(mt, int(fonds + report + r.ca) // 2)
                if mt <= 0:
                    continue
                sorties.append({"date": d, "caisse": cs.nom, "motif": rng.choice(["Petit achat urgent", "Transport", "Monnaie", "Fournitures"]),
                                "montant_ar": mt, "autorise_par": "Responsable d'activité", "anomalie_injectee": False, "source": "synthetique"})
                s_jour += mt
            # sortie anormale (rare)
            if rng.random() < 0.004:
                mt = min(arrondi(rng.uniform(150_000, 400_000)), arrondi((fonds + report + int(r.ca) - s_jour) * 0.8))
                if mt <= 0:
                    continue
                sorties.append({"date": d, "caisse": cs.nom, "motif": "Sortie sans justificatif", "montant_ar": mt,
                                "autorise_par": "", "anomalie_injectee": True, "source": "synthetique"})
                anomalies.append({"date": d, "activite": act, "table": "sorties_caisse", "type": "sortie_sans_justificatif",
                                  "description": f"sortie de {mt} Ar sans autorisation"})
                s_jour += mt
            theorique = fonds + report + int(r.ca) - s_jour
            u = rng.random()
            anomalie = False
            if u < TAUX_ANOMALIE_CLOTURE and theorique > fonds:
                ecart = -arrondi(rng.uniform(0.25, 0.8) * max(int(r.ca), 60_000))
                anomalie = True
                anomalies.append({"date": d, "activite": act, "table": "clotures", "type": "manque_important",
                                  "description": f"écart de {ecart} Ar à la clôture"})
            elif u < 0.80:
                ecart = 0
            else:
                ecart = int(rng.choice([-1, 1]) * arrondi(rng.uniform(500, 6_000)))
            compte = max(0, theorique + ecart)
            statut = "écart à traiter" if abs(ecart) > 10_000 else ("contrôlée" if d <= FIN - timedelta(days=7) else "soumise")
            clotures.append({"date": d, "caisse": cs.nom, "activite": act, "fonds_ar": fonds, "report_ar": report,
                             "encaissements_ar": int(r.ca), "sorties_ar": s_jour, "montant_theorique_ar": theorique,
                             "montant_compte_ar": compte, "ecart_ar": compte - theorique, "statut": statut,
                             "anomalie_injectee": anomalie,
                             "source": "synthetique_sur_ca_reel" if act == "Restaurant" and d <= date(2026, 10, 20) else "synthetique"})
            report = compte - fonds
            if d.weekday() == JOUR_REMISE and report > 0:
                remises.append({"date": d, "caisse": cs.nom, "montant_ar": report, "remis_par": "Caissier", "recu_par": "Comptable", "source": "synthetique"})
                report = 0
    df_s = pd.DataFrame(sorties)
    df_s.insert(0, "sortie_id", range(1, len(df_s) + 1))
    df_c = pd.DataFrame(clotures)
    df_c.insert(0, "cloture_id", range(1, len(df_c) + 1))
    df_r = pd.DataFrame(remises)
    df_r.insert(0, "remise_id", range(1, len(df_r) + 1))
    return df_s, df_c, df_r, anomalies


# ------------------------------------------------------- 4. DÉPENSES
CAT_REELLES = {"legumes_herbes": "Ingrédients", "viande_poisson": "Ingrédients", "laitier_oeufs": "Ingrédients", "epicerie": "Ingrédients",
               "fruits": "Ingrédients", "boissons": "Boissons", "frais_transport": "Transport", "emballage": "Emballages",
               "entretien": "Entretien", "energie": "Énergie", "fournitures": "Fournitures", "tabac": "Tabac (revente)"}


def statut_circuit(montant, d):
    if d > FIN - timedelta(days=5):
        return "à valider PDG" if montant > SEUIL_PDG else rng.choice(["en étude achats", "à valider comptable"])
    return "refusée" if rng.random() < 0.04 else "payée"


def depenses(dossier_reel, df_enc):
    lignes, anomalies = [], []
    a = pd.read_csv(os.path.join(dossier_reel, "achats.csv"))
    a = a[~a.categorie.isin(["retrait_caisse", "hors_restaurant"])]
    for _, r in a.iterrows():
        lignes.append({"date": r.date, "unite": "Restaurant", "categorie": CAT_REELLES.get(r.categorie, "Autres"), "objet": r.produit_fr,
                       "montant_ar": int(r.prix_ar), "statut": "payée", "anomalie_injectee": False, "source": r.source})
    f = pd.read_csv(os.path.join(dossier_reel, "achats_factures_boissons.csv"))
    for _, r in f.iterrows():
        lignes.append({"date": r.date, "unite": "Restaurant", "categorie": "Boissons", "objet": f"{r.article} (facture {r.facture})",
                       "montant_ar": int(r.montant_ar), "statut": "payée", "anomalie_injectee": False, "source": r.source})
    s = pd.read_csv(os.path.join(dossier_reel, "achats_stock_reception.csv"))
    s = s[s.montant_retenu_ar > 0]
    for _, r in s.iterrows():
        lignes.append({"date": r.date, "unite": "Restaurant", "categorie": CAT_REELLES.get(r.categorie, "Autres"), "objet": r.produit,
                       "montant_ar": int(r.montant_retenu_ar), "statut": "payée", "anomalie_injectee": False, "source": r.source})
    # Restaurant après la fin du cahier : achats ≈ 48 % du CA (ratio observé v4), regroupés en 2 à 3 achats par semaine
    ca_r = df_enc[(df_enc.activite == "Restaurant") & (df_enc.source == "synthetique")]
    for d in jours(date(2026, 10, 30), FIN):
        if d.weekday() in (1, 4, 5):
            semaine = ca_r[(pd.to_datetime(ca_r.date) > pd.Timestamp(d) - pd.Timedelta(days=7)) & (pd.to_datetime(ca_r.date) <= pd.Timestamp(d))].montant_ar.sum()
            total = semaine * 0.48 / 3
            for cat, part in [("Ingrédients", 0.6), ("Boissons", 0.35), ("Emballages", 0.05)]:
                m = arrondi(total * part * rng.lognormal(0, 0.25))
                if m:
                    lignes.append({"date": str(d), "unite": "Restaurant", "categorie": cat, "objet": f"Achats {cat.lower()}",
                                   "montant_ar": m, "statut": statut_circuit(m, d), "anomalie_injectee": False, "source": "synthetique"})
    # Autres unités : dépenses récurrentes
    for unite, postes in DEPENSES_UNITES.items():
        for d0 in pd.date_range(DEBUT, FIN, freq="MS"):
            fin_mois = min((d0 + pd.offsets.MonthEnd(0)).date(), FIN)
            nb_j = (fin_mois - d0.date()).days + 1
            for cat, objet, mensuel, freq, profil in postes:
                n = rng.poisson(freq * nb_j / 30) if freq < 1 else max(1, int(round(freq * nb_j / 30)))
                if profil:
                    mensuel *= SAISONS[profil][d0.month]
                for _ in range(n):
                    d = d0.date() + timedelta(days=int(rng.integers(0, nb_j)))
                    m = arrondi(mensuel / max(freq, 1) * rng.lognormal(0, 0.2))
                    anom = rng.random() < 0.01
                    if anom:
                        m = arrondi(m * rng.uniform(3, 5))
                        anomalies.append({"date": d, "activite": unite, "table": "depenses", "type": "prix_anormal",
                                          "description": f"{objet} : {m} Ar (3 à 5 fois le montant habituel)"})
                    lignes.append({"date": str(d), "unite": unite, "categorie": cat, "objet": objet, "montant_ar": m,
                                   "statut": statut_circuit(m, d), "anomalie_injectee": anom, "source": "synthetique"})
    df = pd.DataFrame(lignes)
    df["date"] = pd.to_datetime(df.date).dt.date
    df = df[(df.date >= date(2026, 3, 1)) | (df.unite != "Restaurant")]
    df = df.sort_values(["date", "unite"]).reset_index(drop=True)
    df["validation_pdg_requise"] = df.montant_ar > SEUIL_PDG
    df.insert(0, "depense_id", range(1, len(df) + 1))
    return df, anomalies


def budget_2026(df_dep):
    """Budget mensuel 2026 par unité et catégorie = dépense habituelle × marge ; quelques lignes volontairement sous-dimensionnées."""
    d = df_dep[(df_dep.statut != "refusée") & (~df_dep.anomalie_injectee)].copy()
    d["mois"] = pd.to_datetime(d.date).dt.month
    d["annee"] = pd.to_datetime(d.date).dt.year
    base = d.groupby(["unite", "categorie"]).montant_ar.sum() / d.groupby(["unite", "categorie"]).mois.nunique()
    lignes = []
    sous_dim = set(random.sample(list(base.index), k=max(2, len(base) // 8)))
    for (unite, cat), mensuel in base.items():
        for mois in range(1, 13):
            marge = rng.uniform(0.75, 0.9) if (unite, cat) in sous_dim else rng.uniform(1.0, 1.2)
            lignes.append({"exercice": 2026, "unite": unite, "categorie": cat, "mois": mois,
                           "montant_prevu_ar": arrondi(mensuel * marge, 10_000), "version": 1,
                           "sous_dimensionne": (unite, cat) in sous_dim, "source": "synthetique"})
    df = pd.DataFrame(lignes)
    df.insert(0, "budget_id", range(1, len(df) + 1))
    return df


# ------------------------------------------------------- 5. PRÉSENCES
HORAIRES = {"Gardien de nuit": ("18:00", "06:00"), "Gardien de jour": ("06:00", "18:00"), "Caissier": ("09:00", "18:00"),
            "Chef": ("08:30", "17:30"), "Serveur": ("10:00", "19:00")}


def presences(df_a, df_u):
    lignes = []
    principal = df_a.groupby("employe").first().reset_index()
    for _, e in principal.iterrows():
        intitule, unite = e.poste.split(" – ", 1)
        h1, h2 = HORAIRES.get(intitule, ("08:00", "17:00"))
        assidu = rng.uniform(0.9, 0.99)
        for d in jours(DEBUT_PRESENCES, FIN):
            if not est_ouvert(d, unite):
                continue
            u = rng.random()
            prevu = datetime.combine(d, datetime.strptime(h1, "%H:%M").time())
            if u > assidu:
                statut, arr, dep = "absent", "", ""
                justif = rng.random() < 0.6
            else:
                retard_min = int(rng.exponential(4))
                if rng.random() < 0.08:
                    retard_min += int(rng.integers(11, 60))
                a = prevu + timedelta(minutes=retard_min - int(rng.integers(0, 10)))
                fin = datetime.combine(d, datetime.strptime(h2, "%H:%M").time())
                if fin <= prevu:
                    fin += timedelta(days=1)
                dp = fin + timedelta(minutes=int(rng.integers(-15, 30)))
                statut = "retard" if (a - prevu).total_seconds() > 600 else "présent"
                arr, dep, justif = a.strftime("%Y-%m-%d %H:%M"), dp.strftime("%Y-%m-%d %H:%M"), ""
            lignes.append({"date": d, "employe_id": e.employe_id, "employe": e.employe, "unite": unite,
                           "heure_prevue": h1, "heure_arrivee": arr, "heure_depart": dep, "statut": statut,
                           "absence_justifiee": justif if statut == "absent" else "",
                           "source_saisie": "QR" if rng.random() < 0.93 else "manuel", "source": "synthetique"})
    df = pd.DataFrame(lignes).sort_values(["date", "employe"]).reset_index(drop=True)
    df.insert(0, "presence_id", range(1, len(df) + 1))
    return df


# ------------------------------------------------------------ MAIN
def main(dossier_reel, sortie):
    rj = pd.read_csv(os.path.join(dossier_reel, "restaurant_journalier.csv"), parse_dates=["date"])
    achats = pd.read_csv(os.path.join(dossier_reel, "achats.csv"))
    print("Référentiel")
    df_u, df_p, df_e, df_a, df_cs = referentiel()
    ref = os.path.join(sortie, "00_referentiel")
    ecrire(df_u, ref, "unites.csv"); ecrire(df_p, ref, "postes.csv"); ecrire(df_e, ref, "employes.csv")
    ecrire(df_a, ref, "affectations.csv"); ecrire(df_cs, ref, "caisses.csv")
    cal = _CAL.copy()
    cal["debut"], cal["fin"] = cal.debut.dt.date, cal.fin.dt.date
    ecrire(cal, ref, "calendrier.csv")
    print("Encaissements")
    df_enc, an1 = encaissements(rj)
    ecrire(df_enc, os.path.join(sortie, "01_encaissements"), "encaissements_journaliers.csv")
    print("Caisses")
    df_s, df_c, df_r, an2 = caisses(df_enc, achats, df_cs)
    cdir = os.path.join(sortie, "02_caisses")
    ecrire(df_s, cdir, "sorties_caisse.csv"); ecrire(df_c, cdir, "clotures.csv"); ecrire(df_r, cdir, "remises_fonds.csv")
    print("Dépenses et budget")
    df_d, an3 = depenses(dossier_reel, df_enc)
    ddir = os.path.join(sortie, "03_depenses_budget")
    ecrire(df_d, ddir, "depenses.csv"); ecrire(budget_2026(df_d), ddir, "budget_2026.csv")
    print("Présences")
    ecrire(presences(df_a, df_u), os.path.join(sortie, "04_presences"), "presences.csv")
    an = pd.DataFrame(an1 + an2 + an3).sort_values(["date", "activite"]).reset_index(drop=True)
    an.insert(0, "anomalie_id", range(1, len(an) + 1))
    ecrire(an, sortie, "anomalies_injectees.csv")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage : python generer_donnees_ia.py <dossier_dataset_reel> <dossier_sortie>")
    main(sys.argv[1], sys.argv[2])
